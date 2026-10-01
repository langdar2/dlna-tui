from __future__ import annotations

from .models import Container, Track, to_models


class MusicServer:
    def __init__(self, profile):
        self._p = profile  # async_upnp_client DmsDevice

    async def browse(self, object_id: str = "0") -> list[Container | Track]:
        result = await self._p.async_browse_direct_children(object_id)
        return to_models(result.result)
