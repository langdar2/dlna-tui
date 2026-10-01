"""CrateMind2 "radio": next-best tracks for a seed, resolved to playable URLs.

Chain: seed title -> CrateMind /api/tracks (find its /music/... path) ->
/api/playlists/preview (audio-similarity ranking) -> for each recommended path,
resolve its basename to a VuIO stream_url via VuIO's MCP endpoint over HTTP.
CrateMind and VuIO index the same files; the basename is the bridge.
"""
from __future__ import annotations

import json
import os

import aiohttp

from .models import Track

CRATE_URL = os.environ.get("CRATE_URL", "http://192.168.0.3:8008")
VUIO_URL = os.environ.get("VUIO_URL", "http://192.168.0.3:8080")
_MCP_VERSION = "2026-07-28"


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _pick_seed(candidates: list[dict], artist: str) -> str | None:
    """Best /music/... path among title matches: prefer one whose path also
    mentions the artist (title alone is ambiguous across albums)."""
    if not candidates:
        return None
    a = (artist or "").lower()
    if a:
        for c in candidates:
            if a in c["path"].lower():
                return c["path"]
    return candidates[0]["path"]


def _match_file(files: list[dict], basename: str) -> dict | None:
    """VuIO search returns fuzzy hits; take the exact filename, else the first."""
    for f in files:
        if f.get("filename") == basename:
            return f
    return files[0] if files else None


async def _vuio_search(session: aiohttp.ClientSession, query: str) -> list[dict]:
    body = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {
            "name": "search_media",
            "arguments": {"query": query, "category": "audio", "limit": 10},
            "_meta": {"io.modelcontextprotocol/protocolVersion": _MCP_VERSION},
        },
    }
    headers = {"MCP-Protocol-Version": _MCP_VERSION,
               "Mcp-Method": "tools/call", "Mcp-Name": "search_media"}
    async with session.post(f"{VUIO_URL}/mcp", json=body, headers=headers) as r:
        r.raise_for_status()
        payload = await r.json()
    result = payload["result"]
    data = result.get("structuredContent") or json.loads(result["content"][0]["text"])
    return data.get("files", [])


async def _resolve(session: aiohttp.ClientSession, path: str) -> Track | None:
    files = await _vuio_search(session, _basename(path))
    f = _match_file(files, _basename(path))
    if not f:
        return None
    return Track(
        id=str(f["id"]), title=f.get("title") or _basename(path),
        artist=f.get("artist", ""), album=f.get("album", ""),
        media_url=f["stream_url"],  # directly playable; no DIDL needed
    )


async def radio_tracks(title: str, artist: str = "", limit: int = 10) -> list[Track]:
    """Tracks similar to the given one, as playable Tracks (unresolved ones dropped)."""
    async with aiohttp.ClientSession(raise_for_status=False,
                                     timeout=aiohttp.ClientTimeout(total=15)) as s:
        async with s.get(f"{CRATE_URL}/api/tracks",
                         params={"q": title, "limit": 20}) as r:
            r.raise_for_status()
            candidates = (await r.json()).get("tracks", [])
        seed = _pick_seed(candidates, artist)
        if seed is None:
            return []
        async with s.post(f"{CRATE_URL}/api/playlists/preview",
                          json={"mode": "seed", "seed_path": seed, "limit": limit}) as r:
            r.raise_for_status()
            recs = (await r.json()).get("tracks", [])
        out = []
        for rec in recs:
            if rec["path"] == seed:  # don't recommend the seed back
                continue
            t = await _resolve(s, rec["path"])
            if t:
                out.append(t)
        return out


def _selfcheck() -> None:
    # Pure logic only (no network): seed pick + filename match.
    cand = [{"path": "/music/A - X/01. A - Ruska.flac"},
            {"path": "/music/B - Y/02. B - Ruska.flac"}]
    assert _pick_seed(cand, "B") == "/music/B - Y/02. B - Ruska.flac"
    assert _pick_seed(cand, "") == cand[0]["path"]
    assert _pick_seed([], "B") is None
    files = [{"filename": "other.flac"}, {"filename": "02. B - Ruska.flac"}]
    assert _match_file(files, "02. B - Ruska.flac")["filename"] == "02. B - Ruska.flac"
    assert _match_file(files, "missing.flac")["filename"] == "other.flac"
    assert _match_file([], "x") is None
    print("ok")


if __name__ == "__main__":
    _selfcheck()
