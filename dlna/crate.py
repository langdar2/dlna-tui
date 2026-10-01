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


def _rank_seeds(candidates: list[dict], artist: str, album: str) -> list[str]:
    """Candidate /music/... paths ordered best-first: artist+album, then artist,
    then the rest. Title alone is ambiguous across albums and re-releases, so we
    try them in order until one is an analysed seed CrateMind accepts."""
    a, al = (artist or "").lower(), (album or "").lower()
    scored = []
    for c in candidates:
        p = c["path"].lower()
        score = (2 if a and al and a in p and al in p else
                 1 if a and a in p else 0)
        scored.append((score, c["path"]))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [p for _, p in scored]


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


async def _preview(s: aiohttp.ClientSession, seed: str, limit: int) -> list[dict]:
    """Similarity recommendations for one seed path. [] if CrateMind can't seed it."""
    async with s.post(f"{CRATE_URL}/api/playlists/preview",
                      json={"mode": "seed", "seed_path": seed, "limit": limit}) as r:
        if r.status == 404:  # seed not among analysed tracks -> let caller try the next
            return []
        r.raise_for_status()
        return (await r.json()).get("tracks", [])


async def radio_tracks(title: str, artist: str = "", limit: int = 10,
                       album: str = "") -> list[Track]:
    """Tracks similar to the given one, as playable Tracks (unresolved ones dropped)."""
    async with aiohttp.ClientSession(raise_for_status=False,
                                     timeout=aiohttp.ClientTimeout(total=15)) as s:
        async with s.get(f"{CRATE_URL}/api/tracks",
                         params={"q": title, "limit": 20}) as r:
            r.raise_for_status()
            candidates = (await r.json()).get("tracks", [])
        seeds = _rank_seeds(candidates, artist, album)
        seed, recs = None, []
        for cand in seeds:  # first analysed seed that yields recommendations wins
            recs = await _preview(s, cand, limit)
            if recs:
                seed = cand
                break
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
    cand = [{"path": "/music/A - Gold/01. A - Win.flac"},
            {"path": "/music/A - Singles/02. A - Win.flac"},
            {"path": "/music/C - Mix/03. C - Win.flac"}]
    # album match beats bare artist match beats nothing
    assert _rank_seeds(cand, "A", "Singles")[0] == "/music/A - Singles/02. A - Win.flac"
    assert _rank_seeds(cand, "A", "")[0].startswith("/music/A -")
    assert _rank_seeds([], "A", "x") == []
    files = [{"filename": "other.flac"}, {"filename": "02. B - Ruska.flac"}]
    assert _match_file(files, "02. B - Ruska.flac")["filename"] == "02. B - Ruska.flac"
    assert _match_file(files, "missing.flac")["filename"] == "other.flac"
    assert _match_file([], "x") is None
    print("ok")


if __name__ == "__main__":
    _selfcheck()
