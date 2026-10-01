from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, ListItem, ListView, Label, Tree

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
        ("r", "rescan", "Rescan"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, server: MusicServer, renderer: Renderer, store: Store):
        super().__init__()
        self.server = server
        self.renderer = renderer
        self.store = store
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
        tree = self.query_one("#browser", Tree)
        await self._load_children(tree.root, "0")
        tree.root.expand()
        self.set_interval(1.0, self._refresh_state)
        await self.renderer.subscribe(self._refresh_state)

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
            self.queue = Queue([obj])
            await self.renderer.play(obj)

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _refresh_state(self) -> None:
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
        if not current:
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
        if nxt:
            await self.renderer.play(nxt)

    async def action_prev(self) -> None:
        prv = self.queue.prev()
        if prv:
            await self.renderer.play(prv)

    async def action_enqueue(self) -> None:
        node = self.query_one("#browser", Tree).cursor_node
        obj = self._node_obj.get(node.id) if node else None
        if isinstance(obj, Track):
            self.queue.append(obj)
            self.query_one("#queue", ListView).append(ListItem(Label(obj.title)))

    async def action_vol_up(self) -> None:
        await self.renderer.set_volume(self.renderer.state().volume + 0.05)

    async def action_vol_down(self) -> None:
        await self.renderer.set_volume(self.renderer.state().volume - 0.05)

    async def action_seek_fwd(self) -> None:
        await self.renderer.seek(10)

    async def action_seek_back(self) -> None:
        await self.renderer.seek(-10)

    async def action_search(self) -> None:
        await self.push_screen(SearchScreen(self))

    async def action_favorite(self) -> None:
        node = self.query_one("#browser", Tree).cursor_node
        obj = self._node_obj.get(node.id) if node else None
        if isinstance(obj, Track):
            self.store.favorites.append({"id": obj.id, "title": obj.title,
                                         "media_url": obj.media_url, "didl": obj.didl})
            self.store.save()
            self.notify(f"Favorit: {obj.title}")

    async def action_rescan(self) -> None:
        self.notify("Rescan: Neustart der App nötig (d für Geräte).")

    async def action_quit(self) -> None:
        self.store.save()
        self.exit()


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
