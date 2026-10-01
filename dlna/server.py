from __future__ import annotations

from .models import Container, Track, to_models


class MusicServer:
    def __init__(self, profile):
        self._p = profile  # async_upnp_client DmsDevice

    async def browse(self, object_id: str = "0") -> list[Container | Track]:
        result = await self._p.async_browse_direct_children(object_id)
        return to_models(result.result)

    async def search(self, query: str, container_id: str = "0") -> list[Track]:
        criteria = (
            f'upnp:class derivedfrom "object.item.audioItem" '
            f'and dc:title contains "{query}"'
        )
        try:
            result = await self._p.async_search_directory(container_id, criteria)
            return [o for o in to_models(result.result) if isinstance(o, Track)]
        except Exception:
            # ponytail: server without Search -> browse + local filter.
            items = await self.browse(container_id)
            q = query.lower()
            return [o for o in items if isinstance(o, Track) and q in o.title.lower()]
