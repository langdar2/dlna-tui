from __future__ import annotations

import asyncio

from async_upnp_client.profiles.dlna import DmrDevice, DmsDevice
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, ListItem, ListView, Label, Tree

from dlna.discovery import build_device, discover
from dlna.models import Container, Queue, Track
from dlna.renderer import Renderer
from dlna.server import MusicServer
from dlna.store import Store
from .widgets import NowPlaying


class DlnaApp(App):
    CSS = "Tree { width: 50%; } ListView { width: 50%; }"
    BINDINGS = [
        ("space", "toggle", "Play/Pause"),
        ("n", "next", "Next"),
        ("p", "prev", "Prev"),
        ("a", "enqueue", "Queue"),
        ("plus", "vol_up", "Vol+"),
        ("minus", "vol_down", "Vol-"),
        ("right", "seek_fwd", "Seek+"),
        ("left", "seek_back", "Seek-"),
        ("slash", "search", "Suche"),
        ("f", "favorite", "Fav"),
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

    def compose(self) -> ComposeResult:
        yield Header()
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
        self.set_interval(1.0, self._refresh_state)

    async def set_server(self, info) -> None:
        self.server = MusicServer(
            DmsDevice(await build_device(info, self.requester), self.event_handler))
        self._srv_info = info
        self.store.last_server = info.udn
        self.store.save()
        tree = self.query_one("#browser", Tree)
        tree.root.remove_children()
        self._node_obj.clear()
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
            self.queue = Queue([obj])
            await self.renderer.play(obj)

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _refresh_state(self) -> None:
        if not self.renderer:
            return
        st = self.renderer.state()
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
            await self.push_screen(SearchScreen(self))

    async def action_favorite(self) -> None:
        node = self.query_one("#browser", Tree).cursor_node
        obj = self._node_obj.get(node.id) if node else None
        if isinstance(obj, Track):
            self.store.favorites.append({"id": obj.id, "title": obj.title,
                                         "media_url": obj.media_url, "didl": obj.didl})
            self.store.save()
            self.notify(f"Favorit: {obj.title}")

    async def action_devices(self) -> None:
        await self.push_screen(DeviceScreen(self))

    async def action_quit(self) -> None:
        self.store.save()
        self.exit()


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


class SearchScreen(ModalScreen):
    def __init__(self, app_ref: "DlnaApp"):
        super().__init__()
        self._app = app_ref

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Suche…", id="q")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        results = await self._app.server.search(event.value)
        tree = self._app.query_one("#browser", Tree)
        tree.root.remove_children()
        for t in results:
            child = tree.root.add(t.title, allow_expand=False)
            self._app._node_obj[child.id] = t
        self.dismiss()
