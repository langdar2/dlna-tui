from __future__ import annotations

import asyncio
import os

from async_upnp_client.profiles.dlna import DmrDevice, DmsDevice
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, ListItem, ListView, Label, Static, Tree

from dlna.art import to_ansi
from dlna.crate import radio_tracks, rate, song_key
from dlna.vuio import handoff, media_ids
from dlna.discovery import build_device, discover
from dlna.models import Container, Queue, Track
from dlna.renderer import Renderer
from dlna.server import MusicServer
from dlna.store import Store
from .widgets import NowPlaying


QUEUE_VIEW_MAX = 200  # queue rows to render; see _sync_queue_view


class DlnaApp(App):
    CSS = "Tree { width: 50%; } ListView { width: 50%; } NowPlaying { height: 2; }"
    BINDINGS = [
        ("space", "toggle", "Play/Pause"),
        ("n", "next", "Next"),
        ("p", "prev", "Prev"),
        ("a", "enqueue", "Queue"),
        ("plus", "vol_up", "Vol+"),
        ("minus", "vol_down", "Vol-"),
        ("right", "seek_fwd", "Seek+"),
        ("left", "seek_back", "Seek-"),
        ("slash", "search", "Filter"),
        ("c", "crate_radio", "Radio"),
        ("f", "favorite", "Fav ★"),
        ("b", "ban", "Ban ✗"),
        ("x", "handoff", "An VuIO"),
        ("i", "info", "Info"),
        ("d", "devices", "Geräte"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, store: Store, requester, event_handler,
                 srv_info=None, rnd_info=None):
        super().__init__()
        self.store = store
        self.requester = requester
        self.event_handler = event_handler
        self._srv_info = srv_info
        self._rnd_info = rnd_info
        self.server: MusicServer | None = None
        self.renderer: Renderer | None = None
        self.queue = Queue()
        self._node_obj: dict = {}  # ponytail: grows unbounded on re-search; prune if it matters
        self._last_state = ""
        self._marked = -1  # queue row currently showing the ▶ marker
        self._tasks: set = set()  # keep create_task refs alive (else GC can cancel them)
        self._filter_node = None  # tree node being filtered in place; None = not filtering
        self._filter_cache: dict[str, list] = {}  # cid -> children (one browse per folder)
        self.radio = False  # CrateMind auto-continue: keep queueing similar tracks when it empties
        self._radio_busy = False  # guard against overlapping radio fetches
        self._queue_gen = 0  # bumped when the user replaces the queue; see _append_radio
        self.handed_off = False  # VuIO drives the playlist; we stop advancing
        self.radio_limit = int(os.environ.get("RADIO_LIMIT", "10"))  # tracks per radio fetch
        self._heard: set[str] = set()  # track ids already queued; radio skips them

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="/ Ordner filtern…", id="filter")
        with Horizontal():
            yield Tree("Server", id="browser")
            yield ListView(id="queue")
        yield NowPlaying(id="now")
        yield Footer()

    async def on_mount(self) -> None:
        if self._srv_info:
            await self.set_server(self._srv_info)
        if self._rnd_info:
            await self.set_renderer(self._rnd_info)
        self.query_one("#browser", Tree).focus()  # keys drive playback, not the filter box
        self.set_interval(1.0, self._poll)

    async def set_server(self, info) -> None:
        self.server = MusicServer(
            DmsDevice(await build_device(info, self.requester), self.event_handler))
        self._srv_info = info
        self.store.last_server = info.udn
        self.store.save()
        tree = self.query_one("#browser", Tree)
        tree.root.remove_children()
        self._node_obj.clear()
        self._filter_cache.clear()
        self._filter_node = None
        await self._load_children(tree.root, "0")
        tree.root.expand()
        self._update_subtitle()

    async def set_renderer(self, info) -> None:
        self.renderer = Renderer(
            DmrDevice(await build_device(info, self.requester), self.event_handler),
            on_error=lambda m: self.notify(m, severity="error"))
        self._rnd_info = info
        self.store.last_renderer = info.udn
        self.store.save()
        self._last_state = ""
        await self.renderer.subscribe(self._refresh_state)
        self._update_subtitle()

    def _update_subtitle(self) -> None:
        srv = self._srv_info.name if self._srv_info else "—"
        rnd = self._rnd_info.name if self._rnd_info else "—"
        radio = "  📻 Radio" if self.radio else ""
        if self.handed_off:
            radio = "  ⇢ VuIO"
        self.sub_title = f"{srv} → {rnd}{radio}"

    async def _load_children(self, node, object_id: str) -> None:
        for obj in await self.server.browse(object_id):
            child = node.add(obj.title, allow_expand=isinstance(obj, Container))
            self._node_obj[child.id] = obj

    async def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        obj = self._node_obj.get(event.node.id)
        if isinstance(obj, Container) and not event.node.children:
            await self._load_children(event.node, obj.id)

    async def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        obj = self._node_obj.get(event.node.id)
        if isinstance(obj, Track):
            if not self.renderer:
                self.notify("Kein Renderer gewählt (d)", severity="warning")
                return
            # Queue every track in the same folder/album, starting at this one, so
            # playback continues automatically. Use the real folder contents, not
            # the visible tree nodes, so a filter doesn't truncate the queue.
            cid = self._container_id_of(event.node.parent) if event.node.parent else "0"
            tracks = [t for t in await self._folder_items(cid) if isinstance(t, Track)]
            idx = next((i for i, t in enumerate(tracks) if t.id == obj.id), -1)
            if idx < 0:  # track not in that folder listing (e.g. root-level item)
                tracks, idx = [obj], 0
            self.queue = Queue(tracks, idx)
            self._queue_gen += 1  # strand any radio fetch still running for the old song
            self.handed_off = False  # we're driving again
            self.radio = False  # user picked a track; stop auto-continuing
            self._update_subtitle()
            await self.renderer.play(obj)  # start audio first; the pane can lag
            await self._sync_queue_view()

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _poll(self) -> None:
        # Interval tick: refresh cached position/volume, then redraw.
        if self.renderer:
            await self.renderer.update()
        self._refresh_state()

    def _refresh_state(self) -> None:
        if not self.renderer:
            return
        st = self.renderer.state()
        # Many renderers don't echo media_title back via GENA; fall back to the
        # track we queued so "nichts spielt" doesn't show while audio plays.
        current = self.queue.current()
        if current:
            if not st.title:
                st.title = current.title
            st.info = current.info
        self.query_one("#now", NowPlaying).st = st
        self._mark_current()  # every index change lands here, whoever caused it
        # Advance only on the PLAYING->STOPPED edge; level-triggering would skip
        # tracks while the renderer sits in STOPPED for several ticks before the
        # next one reports PLAYING.
        if (st.transport_state == "STOPPED" and self._last_state not in ("", "STOPPED")
                and not self.handed_off):  # VuIO advances its own playlist
            nxt = self.queue.advance()
            if nxt:
                self._spawn(self.renderer.play(nxt))
            elif self.radio and not self._radio_busy:
                self._spawn(self._radio_continue())  # queue ran dry -> fetch more
        self._last_state = st.transport_state

    async def action_toggle(self) -> None:
        current = self.queue.current()
        if not current or not self.renderer:
            return
        state = self.renderer.state().transport_state
        if state == "PLAYING":
            await self.renderer.pause()
        elif state == "PAUSED_PLAYBACK":
            await self.renderer.resume()
        else:
            await self.renderer.play(current)

    async def action_next(self) -> None:
        nxt = self.queue.advance()
        if nxt and self.renderer:
            await self.renderer.play(nxt)

    async def action_prev(self) -> None:
        prv = self.queue.prev()
        if prv and self.renderer:
            await self.renderer.play(prv)

    async def action_enqueue(self) -> None:
        node = self.query_one("#browser", Tree).cursor_node
        obj = self._node_obj.get(node.id) if node else None
        if isinstance(obj, Track):
            self.queue.append(obj)
            last = len(self.queue.tracks) - 1
            qview = self.query_one("#queue", ListView)
            if len(qview.children) == last:  # view in sync and under the cap
                qview.append(ListItem(Label(self._queue_label(last))))

    async def action_vol_up(self) -> None:
        if self.renderer:
            await self.renderer.set_volume(self.renderer.state().volume + 0.05)

    async def action_vol_down(self) -> None:
        if self.renderer:
            await self.renderer.set_volume(self.renderer.state().volume - 0.05)

    async def action_seek_fwd(self) -> None:
        if self.renderer:
            await self.renderer.seek(10)

    async def action_seek_back(self) -> None:
        if self.renderer:
            await self.renderer.seek(-10)

    async def action_search(self) -> None:
        if self.server:
            self.query_one("#filter", Input).focus()

    def _current_container_node(self):
        """The tree node whose children are 'the current folder' for filtering."""
        tree = self.query_one("#browser", Tree)
        node = tree.cursor_node
        if node is None:
            return tree.root
        obj = self._node_obj.get(node.id)
        if isinstance(obj, Container):
            return node  # cursor sits on a folder -> filter its contents
        return node.parent or tree.root  # cursor on a leaf -> filter its folder

    def _container_id_of(self, node) -> str:
        obj = self._node_obj.get(node.id)
        return obj.id if isinstance(obj, Container) else "0"

    async def _folder_items(self, cid: str) -> list:
        if cid not in self._filter_cache:
            self._filter_cache[cid] = await self.server.browse(cid)
        return self._filter_cache[cid]

    async def _fill(self, node, cid: str, q: str = "") -> None:
        node.remove_children()
        for o in await self._folder_items(cid):
            if q in o.title.lower():  # folders match too, not just tracks
                child = node.add(o.title, allow_expand=isinstance(o, Container))
                self._node_obj[child.id] = o
        node.expand()

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "filter" or not self.server:
            return
        q = event.value.strip().lower()
        if not q:  # cleared: restore the folder's full contents in place
            node, self._filter_node = self._filter_node, None
            if node is not None:
                await self._fill(node, self._container_id_of(node))
            return
        if self._filter_node is None:  # keep ancestors; filter only this folder's node
            self._filter_node = self._current_container_node()
        await self._fill(self._filter_node, self._container_id_of(self._filter_node), q)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter":  # Enter: jump into the filtered results
            self._focus_results()

    def _focus_results(self) -> None:
        """Move focus from the filter box onto the first result so it's playable."""
        tree = self.query_one("#browser", Tree)
        tree.focus()
        node = self._filter_node or tree.root
        if node.children:
            tree.move_cursor(node.children[0])

    def on_key(self, event) -> None:
        if event.key == "down" and getattr(self.focused, "id", None) == "filter":
            event.stop()
            self._focus_results()

    def _seed_track(self) -> Track | None:
        """What to base radio on: the cursor track, else what's playing."""
        node = self.query_one("#browser", Tree).cursor_node
        obj = self._node_obj.get(node.id) if node else None
        return obj if isinstance(obj, Track) else self.queue.current()

    def _queue_label(self, i: int) -> str:
        t = self.queue.tracks[i]
        # Pad the others so titles stay aligned when the marker moves.
        mark = "▶ " if i == self.queue.index else "  "
        rating = {1: " ★", -1: " ✗"}.get(self.store.rating_of(t.id), "")
        return f"{mark}{t.title}{rating}"

    async def _sync_queue_view(self) -> None:
        qview = self.query_one("#queue", ListView)
        await qview.clear()
        # ponytail: cap the rows. An album plus radio stays far under this, but
        # the server's flat "All Music" holds thousands, and mounting that many
        # widgets freezes the UI for seconds. Past the cap the pane shows the
        # head of the queue and _mark_current leaves the marker alone; paginate
        # if browsing huge flat folders ever becomes a real workflow.
        for i in range(min(len(self.queue.tracks), QUEUE_VIEW_MAX)):
            qview.append(ListItem(Label(self._queue_label(i))))
        self._marked = self.queue.index

    def _mark_current(self, force: bool = False) -> None:
        """Move the ▶ marker to the playing track. Touches only the two rows
        that change, so browsing the queue isn't interrupted by a redraw.
        `force` also redraws when the index is unchanged but a label is not —
        after a rating, whose ★/✗ sits in the same row."""
        if self._marked == self.queue.index and not force:
            return
        items = list(self.query_one("#queue", ListView).children)
        if len(items) != len(self.queue.tracks):
            return  # view not in sync (manual adds); next _sync_queue_view redraws
        for i in (self._marked, self.queue.index):
            if 0 <= i < len(items):
                items[i].query_one(Label).update(self._queue_label(i))
        self._marked = self.queue.index

    async def _append_radio(self, seed: Track) -> int | None:
        """Fetch similar tracks for seed and append to the queue, skipping ones
        already heard this session. Returns how many were actually added, or
        None if the user replaced the queue while the fetch was in flight."""
        # Keyed by song, not file id: the same track off a compilation or as a
        # remaster is a different id but the same thing to listen to.
        self._heard.update(song_key(t.artist, t.title) for t in self.queue.tracks)
        gen = self._queue_gen
        recs = await radio_tracks(seed.title, seed.artist, self.radio_limit,
                                  seed.album, seed.media_url)
        if gen != self._queue_gen:
            return None  # these belong to a song the user has since moved on from
        added = 0
        for t in recs:
            key = song_key(t.artist, t.title)
            if key in self._heard:
                continue
            self._heard.add(key)
            self.queue.append(t)
            added += 1
        if added:
            await self._sync_queue_view()
        return added

    async def action_handoff(self) -> None:
        """Give the queue to VuIO so it survives this app closing."""
        if not self.queue.tracks:
            self.notify("Queue ist leer", severity="warning")
            return
        if not self._rnd_info:
            self.notify("Kein Renderer gewählt (d)", severity="warning")
            return
        if media_ids(self.queue.tracks) is None:
            self.notify("Queue enthält Titel, die VuIO nicht kennt", severity="warning")
            return
        self.notify("Übergebe Queue an VuIO…")
        # Set this before releasing the renderer: stopping it raises the
        # PLAYING->STOPPED edge, and we must not treat that as "advance".
        self.handed_off = True
        try:
            n, proto = await handoff(
                self.queue.tracks, self._rnd_info.udn, self._rnd_info.location,
                self.queue.index, f"dlna-tui: {self.queue.current().title}")
        except Exception as exc:  # never claim a handoff that didn't happen
            self.handed_off = False
            self.notify(f"Übergabe fehlgeschlagen: {exc}", severity="error")
            return
        self.radio = False  # VuIO owns the playlist now
        self._update_subtitle()
        self.notify(f"{n} Titel an VuIO übergeben ({proto}) – läuft ohne die App weiter")

    async def action_crate_radio(self) -> None:
        seed = self._seed_track()
        if not seed:
            self.notify("Kein Track für Radio (erst abspielen/auswählen)", severity="warning")
            return
        self.notify(f"Radio: suche Ähnliches zu {seed.title}…")
        # Switching to radio means leaving the album: drop what the folder
        # queued behind the current track, or the suggestions would only start
        # playing after the whole rest of it. Those tracks count as heard, so
        # radio doesn't hand straight back what was just skipped.
        idle = self.queue.current() is None
        self._heard.update(song_key(t.artist, t.title) for t in self.queue.tracks)
        self.queue.drop_after_current()
        n = await self._append_radio(seed)
        if n is None:  # user picked another track meanwhile; don't hijack its queue
            return
        self.radio = True  # keep going automatically when the queue later empties
        self._update_subtitle()
        if n and idle and self.renderer:  # nothing was playing -> start the radio
            nxt = self.queue.current()
            if nxt:
                await self.renderer.play(nxt)
        self.notify(f"Radio an – {n} Titel ergänzt" if n else "Radio: nichts Neues gefunden",
                    severity="information" if n else "warning")

    async def _radio_continue(self) -> None:
        self._radio_busy = True
        try:
            seed = self.queue.current()
            if not (seed and self.renderer):
                return
            if await self._append_radio(seed):
                nxt = self.queue.advance()
                if nxt:
                    await self.renderer.play(nxt)
        finally:
            self._radio_busy = False

    def _rating_target(self) -> Track | None:
        """What to rate: the cursor track, else what's playing."""
        node = self.query_one("#browser", Tree).cursor_node
        obj = self._node_obj.get(node.id) if node else None
        return obj if isinstance(obj, Track) else self.queue.current()

    async def _rate(self, wanted: int, word: str) -> None:
        """Rate the current track, or clear the rating if it already has it."""
        obj = self._rating_target()
        if not obj:
            self.notify("Kein Track gewählt", severity="warning")
            return
        rating = 0 if self.store.rating_of(obj.id) == wanted else wanted
        try:
            known = await rate(obj.media_url, rating, obj.title, obj.artist, obj.album)
        except Exception as exc:
            self.notify(f"CrateMind nicht erreicht: {exc}", severity="error")
            return
        # Store locally either way: the rating still shows in the player, and
        # CrateMind simply has no analysis to attach it to.
        self.store.set_rating(obj.id, rating, obj.title)
        self._mark_current(force=True)
        if rating == 0:
            self.notify(f"Bewertung entfernt: {obj.title}")
        else:
            self.notify(f"{word}: {obj.title}"
                        + ("" if known else " (CrateMind kennt ihn nicht)"),
                        severity="information" if known else "warning")

    async def action_favorite(self) -> None:
        await self._rate(1, "Favorit ★")

    async def action_ban(self) -> None:
        await self._rate(-1, "Nicht mehr spielen ✗")

    async def action_info(self) -> None:
        node = self.query_one("#browser", Tree).cursor_node
        obj = self._node_obj.get(node.id) if node else None
        if not isinstance(obj, Track):
            obj = self.queue.current()
        if isinstance(obj, Track):
            await self.push_screen(TrackInfoScreen(obj))
        else:
            self.notify("Kein Track ausgewählt", severity="warning")

    async def action_devices(self) -> None:
        await self.push_screen(DeviceScreen(self))

    async def action_quit(self) -> None:
        self.store.save()
        self.exit()


def _http_get(url: str) -> bytes:
    # Binary-safe, stdlib: AiohttpRequester decodes bodies to text, which
    # corrupts image bytes. Run under asyncio.to_thread (blocking urlopen).
    import urllib.request
    with urllib.request.urlopen(url, timeout=5) as resp:
        return resp.read()


class TrackInfoScreen(ModalScreen):
    BINDINGS = [("escape", "close", "Schließen"), ("i", "close", "Schließen")]
    CSS = ("TrackInfoScreen { align: center middle; } "
           "#info_box { width: 80%; max-width: 100; height: auto; max-height: 90%; "
           "border: round $accent; padding: 1 2; } "
           "#info_box Static { width: 1fr; }")

    def __init__(self, track: Track):
        super().__init__()
        self.track = track

    def compose(self) -> ComposeResult:
        t = self.track
        lines = [f"Titel:  {t.title}"]
        for label, val in (("Artist", t.artist), ("Album", t.album),
                           ("Dauer", t.duration), ("Media", t.info)):
            if val:
                lines.append(f"{label}:{' ' * (7 - len(label))}{val}")
        lines.append(f"URL:    {t.media_url}")
        with Vertical(id="info_box"):
            yield Static("\n".join(lines))
            yield Static("Cover lädt…" if t.art_uri else "(kein Cover)", id="cover")
            yield Label("[dim]Esc / i schließt[/]")

    async def on_mount(self) -> None:
        if not self.track.art_uri:
            return
        # Match the cover to the box: 80% of the terminal (capped at 100), minus
        # border + padding, so it fills the modal on any size without overflowing.
        box_w = min(int(self.app.size.width * 0.8), 100)
        cover_w = max(20, box_w - 6)
        try:
            data = await asyncio.to_thread(_http_get, self.track.art_uri)
            art = to_ansi(data, width=cover_w)
        except Exception as exc:  # ponytail: cover is best-effort, never fatal
            art = f"(Cover fehlgeschlagen: {exc})"
        self.query_one("#cover", Static).update(art)

    def action_close(self) -> None:
        self.dismiss()


class DeviceItem(ListItem):
    def __init__(self, info, kind: str):
        super().__init__(Label(info.name))
        self.info = info
        self.kind = kind


class DeviceScreen(ModalScreen):
    BINDINGS = [("escape", "close", "Schließen")]
    CSS = "DeviceScreen { align: center middle; } ListView { width: 60%; height: auto; }"

    def __init__(self, app_ref: "DlnaApp"):
        super().__init__()
        self._app = app_ref

    def compose(self) -> ComposeResult:
        yield Label("Server (Enter wählt):")
        yield ListView(id="pick_servers")
        yield Label("Renderer (Enter wählt):")
        yield ListView(id="pick_renderers")
        yield Label("Esc schließt")

    async def on_mount(self) -> None:
        servers, renderers = await discover()
        sv = self.query_one("#pick_servers", ListView)
        for d in servers:
            sv.append(DeviceItem(d, "server"))
        rv = self.query_one("#pick_renderers", ListView)
        for d in renderers:
            rv.append(DeviceItem(d, "renderer"))

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if item.kind == "server":
            await self._app.set_server(item.info)
            self._app.notify(f"Server: {item.info.name}")
        else:
            await self._app.set_renderer(item.info)
            self._app.notify(f"Renderer: {item.info.name}")
        self.dismiss()

    def action_close(self) -> None:
        self.dismiss()
