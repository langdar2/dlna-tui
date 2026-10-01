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
            # ponytail: server without Search (e.g. VuIO) -> bounded recursive
            # browse + local filter. Caps keep a huge library from hanging the UI;
            # raise them if deep collections get truncated.
            return await self._browse_search(query, container_id)

    async def _browse_search(self, query: str, root_id: str,
                             limit: int = 200, max_nodes: int = 800) -> list[Track]:
        q = query.lower()
        out: list[Track] = []
        pending = [root_id]
        visited = 0
        while pending and len(out) < limit and visited < max_nodes:
            visited += 1
            for item in await self.browse(pending.pop(0)):
                if isinstance(item, Container):
                    pending.append(item.id)
                elif q in item.title.lower() or q in item.artist.lower() \
                        or q in item.album.lower():
                    out.append(item)
                    if len(out) >= limit:
                        break
        return out
