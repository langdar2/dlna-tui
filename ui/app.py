from __future__ import annotations

import asyncio

from async_upnp_client.profiles.dlna import DmrDevice, DmsDevice
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, ListItem, ListView, Label, Static, Tree

from dlna.art import to_ansi
from dlna.discovery import build_device, discover
from dlna.models import Container, Queue, Track
from dlna.renderer import Renderer
from dlna.server import MusicServer
from dlna.store import Store
from .widgets import NowPlaying


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
        ("f", "favorite", "Fav"),
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
        self._tasks: set = set()  # keep create_task refs alive (else GC can cancel them)
        self._filter_cid: str | None = None  # container being filtered; None = not filtering
        self._filter_cache: dict[str, list] = {}  # cid -> children (one browse per folder)

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
        self._filter_cid = None
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
        self.sub_title = f"{srv} → {rnd}"

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
            # Queue every track in the same folder/album, starting at this one,
            # so playback continues through the rest of the list automatically.
            parent = event.node.parent
            siblings = parent.children if parent else [event.node]
            tracks = [t for t in (self._node_obj.get(n.id) for n in siblings)
                      if isinstance(t, Track)]
            self.queue = Queue(tracks, tracks.index(obj))
            await self.renderer.play(obj)

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
        # Advance only on the PLAYING->STOPPED edge; level-triggering would skip
        # tracks while the renderer sits in STOPPED for several ticks before the
        # next one reports PLAYING.
        if st.transport_state == "STOPPED" and self._last_state not in ("", "STOPPED"):
            nxt = self.queue.advance()
            if nxt:
                self._spawn(self.renderer.play(nxt))
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
            self.query_one("#queue", ListView).append(ListItem(Label(obj.title)))

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

    def _current_container_id(self) -> str:
        """Container whose children are 'the current folder' for filtering."""
        node = self.query_one("#browser", Tree).cursor_node
        obj = self._node_obj.get(node.id) if node else None
        if isinstance(obj, Container):
            return obj.id
        parent = self._node_obj.get(node.parent.id) if node and node.parent else None
        return parent.id if isinstance(parent, Container) else "0"

    async def _folder_items(self, cid: str) -> list:
        if cid not in self._filter_cache:
            self._filter_cache[cid] = await self.server.browse(cid)
        return self._filter_cache[cid]

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "filter" or not self.server:
            return
        tree = self.query_one("#browser", Tree)
        q = event.value.strip().lower()
        if not q:  # cleared: reload the folder we were filtering (or top level)
            cid, self._filter_cid = self._filter_cid or "0", None
            tree.root.remove_children()
            await self._load_children(tree.root, cid)
            tree.root.expand()
            return
        if self._filter_cid is None:  # capture folder before we flatten the tree
            self._filter_cid = self._current_container_id()
        tree.root.remove_children()
        for o in await self._folder_items(self._filter_cid):
            if isinstance(o, Track) and q in o.title.lower():
                child = tree.root.add(o.title, allow_expand=False)
                self._node_obj[child.id] = o
        tree.root.expand()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter":  # Enter: hand control back to the browser
            self.query_one("#browser", Tree).focus()

    async def action_favorite(self) -> None:
        node = self.query_one("#browser", Tree).cursor_node
        obj = self._node_obj.get(node.id) if node else None
        if isinstance(obj, Track):
            self.store.favorites.append({"id": obj.id, "title": obj.title,
                                         "media_url": obj.media_url, "didl": obj.didl})
            self.store.save()
            self.notify(f"Favorit: {obj.title}")

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
