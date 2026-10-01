from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Callable

from .models import Track


@dataclass
class RendererState:
    transport_state: str = ""
    position: int = 0
    duration: int = 0
    volume: float = 0.0
    title: str = ""
    info: str = ""  # set by the app from the queued track; renderers rarely report it


class Renderer:
    def __init__(self, profile, on_error: Callable[[str], None] | None = None):
        self._p = profile  # async_upnp_client DmrDevice
        self._on_error = on_error or (lambda msg: None)

    async def _safe(self, coro) -> bool:
        try:
            await coro
            return True
        except Exception as exc:  # ponytail: UI must never die from UPnP errors
            self._on_error(str(exc))
            return False

    def state(self) -> RendererState:
        ts = self._p.transport_state  # str-subclass enum; .value gives "PLAYING" etc.
        return RendererState(
            transport_state=getattr(ts, "value", ts) or "",
            position=int(self._p.media_position or 0),
            duration=int(self._p.media_duration or 0),
            volume=float(self._p.volume_level or 0.0),
            title=self._p.media_title or "",
        )

    async def play(self, track: Track) -> bool:
        async def _go():
            await self._p.async_set_transport_uri(
                track.media_url, track.title, track.didl or None)
            await self._p.async_play()
        return await self._safe(_go())

    async def pause(self) -> bool:
        return await self._safe(self._p.async_pause())

    async def resume(self) -> bool:
        # Resume from PAUSED without re-setting the transport URI (which restarts at 0:00).
        return await self._safe(self._p.async_play())

    async def stop(self) -> bool:
        return await self._safe(self._p.async_stop())

    async def next(self) -> bool:
        return await self._safe(self._p.async_next())

    async def previous(self) -> bool:
        return await self._safe(self._p.async_previous())

    async def seek(self, seconds: int) -> bool:
        # DmrDevice.async_seek_rel_time expects datetime.timedelta, not int
        return await self._safe(
            self._p.async_seek_rel_time(datetime.timedelta(seconds=seconds))
        )

    async def set_volume(self, level: float) -> bool:
        level = max(0.0, min(1.0, level))
        return await self._safe(self._p.async_set_volume_level(level))

    async def update(self) -> bool:
        # Polls GetPositionInfo/GetVolume etc. GENA events don't tick position
        # or report volume, so state() is stale without this.
        return await self._safe(self._p.async_update())

    async def subscribe(self, on_event: Callable[[], None]) -> bool:
        self._p.on_event = lambda svc, vars: on_event()
        return await self._safe(self._p.async_subscribe_services(auto_resubscribe=True))
