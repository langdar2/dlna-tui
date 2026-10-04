"""CrateMind2 "radio": next-best tracks for a seed, resolved to playable URLs.

Chain: seed title -> CrateMind /api/tracks (find its /music/... path) ->
/api/playlists/preview (audio-similarity ranking) -> for each recommended path,
resolve its basename to a VuIO stream_url via VuIO's MCP endpoint over HTTP.
CrateMind and VuIO index the same files; the basename is the bridge.
"""
from __future__ import annotations

import json
import os
import re

import aiohttp

from .models import Track

CRATE_URL = os.environ.get("CRATE_URL", "http://192.168.0.3:8008")
VUIO_URL = os.environ.get("VUIO_URL", "http://192.168.0.3:8080")
_MCP_VERSION = "2026-07-28"

# The same files, mounted differently: CrateMind analysed them under MUSIC_DIR,
# VuIO indexes them under their real host path. Mirrors CrateMind's own
# vuio_client.to_vuio_path. ponytail: single prefix swap, like upstream; a real
# mapping table only if either side ever serves multiple music roots.
MUSIC_DIR = os.environ.get("MUSIC_DIR", "/music")
VUIO_MUSIC_DIR = os.environ.get("VUIO_MUSIC_DIR", "/Volumes/Platte/Musik")


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _to_crate_path(vuio_path: str) -> str:
    """VuIO host path -> the /music/... path CrateMind keys its tracks by."""
    if vuio_path.startswith(VUIO_MUSIC_DIR + "/"):
        return MUSIC_DIR + vuio_path[len(VUIO_MUSIC_DIR):]
    return vuio_path


def _to_vuio_path(crate_path: str) -> str:
    if crate_path.startswith(MUSIC_DIR + "/"):
        return VUIO_MUSIC_DIR + crate_path[len(MUSIC_DIR):]
    return crate_path


def _media_id(media_url: str) -> str:
    """Numeric VuIO id from a stream/media URL (.../media/42380 or .../media/42380.m4a)."""
    tail = media_url.rsplit("/", 1)[-1].split(".", 1)[0]
    return tail if tail.isdigit() else ""


def _crate_query(filename: str, title: str) -> str:
    """CrateMind matches on the file PATH, so the basename is the reliable key;
    the ID3 title often differs (punctuation like "What's Up?", "feat.", remaster
    tags). Use the basename stem minus its leading track-number; fall back to title."""
    if not filename:
        return title
    stem = filename.rsplit(".", 1)[0]
    stem = re.sub(r"^\s*\d+\s*[.\-)]\s*", "", stem)  # "03. Artist - X" -> "Artist - X"
    return stem or title


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


def _match_file(files: list[dict], crate_path: str) -> dict | None:
    """VuIO search returns fuzzy hits. Take the one whose path IS this track —
    basename alone picks the wrong album when a song sits on a compilation too.
    Fall back to basename, then first hit, so a moved file still resolves."""
    want_path, want_name = _to_vuio_path(crate_path), _basename(crate_path)
    for f in files:
        if f.get("path") == want_path:
            return f
    for f in files:
        if f.get("filename") == want_name:
            return f
    return files[0] if files else None


async def _vuio_call(session: aiohttp.ClientSession, tool: str, args: dict) -> dict:
    body = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {
            "name": tool, "arguments": args,
            "_meta": {"io.modelcontextprotocol/protocolVersion": _MCP_VERSION},
        },
    }
    headers = {"MCP-Protocol-Version": _MCP_VERSION,
               "Mcp-Method": "tools/call", "Mcp-Name": tool}
    async with session.post(f"{VUIO_URL}/mcp", json=body, headers=headers) as r:
        r.raise_for_status()
        payload = await r.json()
    result = payload["result"]
    return result.get("structuredContent") or json.loads(result["content"][0]["text"])


async def _vuio_search(session: aiohttp.ClientSession, query: str) -> list[dict]:
    data = await _vuio_call(session, "search_media",
                            {"query": query, "category": "audio", "limit": 10})
    return data.get("files", [])


async def _vuio_path(session: aiohttp.ClientSession, media_id: str) -> str:
    """Exact host path for a VuIO id. Prefix-swapped this IS CrateMind's track key,
    so the seed needs no searching or guessing by title."""
    try:
        data = await _vuio_call(session, "get_media_info", {"file_id": int(media_id)})
    except Exception:  # ponytail: best-effort; title search stays the fallback
        return ""
    return data.get("path", "")


async def _resolve(session: aiohttp.ClientSession, path: str) -> Track | None:
    files = await _vuio_search(session, _basename(path))
    f = _match_file(files, path)
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
                       album: str = "", media_url: str = "") -> list[Track]:
    """Tracks similar to the given one, as playable Tracks (unresolved ones dropped)."""
    async with aiohttp.ClientSession(raise_for_status=False,
                                     timeout=aiohttp.ClientTimeout(total=15)) as s:
        # Exact seed first: the VuIO id gives this file's host path, which
        # prefix-swapped is CrateMind's own key — no title search, no guessing
        # which album. Only if CrateMind hasn't analysed that exact file do we
        # fall back to finding another copy of the song by name.
        mid = _media_id(media_url)
        vuio_path = await _vuio_path(s, mid) if mid else ""
        seed, recs = None, []
        if vuio_path:
            seed_path = _to_crate_path(vuio_path)
            recs = await _preview(s, seed_path, limit)
            seed = seed_path if recs else None
        if not recs:
            async with s.get(f"{CRATE_URL}/api/tracks",
                             params={"q": _crate_query(_basename(vuio_path), title),
                                     "limit": 20}) as r:
                r.raise_for_status()
                candidates = (await r.json()).get("tracks", [])
            for cand in _rank_seeds(candidates, artist, album):
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
    # exact path beats same-basename hit from another album; prefix swap round-trips
    v = VUIO_MUSIC_DIR
    assert _to_crate_path(v + "/A - Gold/01. x.flac") == "/music/A - Gold/01. x.flac"
    assert _to_crate_path("/elsewhere/x.flac") == "/elsewhere/x.flac"
    assert _to_vuio_path(_to_crate_path(v + "/A/01. x.flac")) == v + "/A/01. x.flac"
    files = [{"filename": "01. x.flac", "path": v + "/Comp - Hits/01. x.flac"},
             {"filename": "01. x.flac", "path": v + "/A - Gold/01. x.flac"}]
    assert _match_file(files, "/music/A - Gold/01. x.flac")["path"].endswith("A - Gold/01. x.flac")
    assert _match_file(files, "/music/Moved - Elsewhere/01. x.flac")["filename"] == "01. x.flac"
    assert _match_file([], "/music/x.flac") is None
    # media id extraction from stream/media URLs
    assert _media_id("http://h/media/42380.m4a") == "42380"
    assert _media_id("http://h/media/42380") == "42380"
    assert _media_id("http://h/stream/foo.mp3") == ""
    # crate query: basename stem (minus track number) beats the ID3 title
    assert _crate_query("03. 4 Non Blondes - What's Up.m4a", "What's Up?") \
        == "4 Non Blondes - What's Up"
    assert _crate_query("", "Fallback Title") == "Fallback Title"
    print("ok")


if __name__ == "__main__":
    _selfcheck()
