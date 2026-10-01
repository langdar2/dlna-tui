from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static

from dlna.renderer import RendererState


def _fmt(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


class NowPlaying(Static):
    st: reactive[RendererState | None] = reactive(None)

    def render(self) -> str:
        if not self.st or not self.st.title:
            return "— nichts spielt —"
        s = self.st
        return (f"▶ {s.title}   {_fmt(s.position)}/{_fmt(s.duration)}   "
                f"vol {int(s.volume * 100)}%   [{s.transport_state}]")
