"""CrateMind2 "radio": next-best tracks for a seed, resolved to playable URLs.

Chain: seed title -> CrateMind /api/tracks (find its /music/... path) ->
/api/playlists/preview (audio-similarity ranking) -> for each recommended path,
resolve its basename to a VuIO stream_url via VuIO's MCP endpoint over HTTP.
CrateMind and VuIO index the same files; the basename is the bridge.
"""
from __future__ import annotations

import os
import re

import aiohttp

from .models import Track
from .vuio import call as vuio_call

CRATE_URL = os.environ.get("CRATE_URL", "http://192.168.0.3:8008")


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _common_tail(a: str, b: str) -> int:
    """How many trailing path components two paths share."""
    n = 0
    for x, y in zip(reversed(a.rstrip("/").split("/")),
                    reversed(b.rstrip("/").split("/"))):
        if x != y:
            break
        n += 1
    return n


def _best_match(paths: list[str], want: str) -> str | None:
    """The path that is the same file as `want`, across differently-mounted roots.

    The two services mount one library under different roots
    (/Volumes/Platte/Musik here, /music in CrateMind) but agree on everything
    below it, so the deepest matching tail wins — no side needs the other's
    prefix, and nesting deeper than <album>/<file> just raises the bar.
    Needs two components, since a bare filename collides with the same song on
    a compilation. A tie is genuinely ambiguous (two albums of the same name),
    so give up and let the caller fall back rather than pick arbitrarily.
    """
    scored = sorted(((_common_tail(p, want), p) for p in paths), reverse=True)
    if not want or not scored or scored[0][0] < 2:
        return None
    if len(scored) > 1 and scored[1][0] == scored[0][0]:
        return None
    return scored[0][1]


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


_QUALIFIER = re.compile(r"[(\[][^)\]]*[)\]]")  # "(2025 Remastered)", "(Edit)", …
_NOISE = re.compile(r"[^a-z0-9]+")


def song_key(artist: str, title: str, path: str = "") -> str:
    """Identity of a song regardless of which album it came off.

    Radio otherwise follows a track with its own copy from a compilation, or
    with the remaster sitting next to it — different files, same thing to
    listen to. Falls back to the filename when a file carries no tags.
    """
    base = f"{artist} {title}".strip() or _crate_query(_basename(path), "")
    return _NOISE.sub("", _QUALIFIER.sub(" ", base.lower()))


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
    """VuIO search returns fuzzy hits. Take the one that is this exact file,
    else any with the right name, else the first."""
    best = _best_match([f["path"] for f in files if f.get("path")], crate_path)
    if best:
        return next(f for f in files if f.get("path") == best)
    for f in files:
        if f.get("filename") == _basename(crate_path):
            return f
    return files[0] if files else None


async def _vuio_search(session: aiohttp.ClientSession, query: str) -> list[dict]:
    data = await vuio_call(session, "search_media",
                            {"query": query, "category": "audio", "limit": 10})
    return data.get("files", [])


async def _vuio_path(session: aiohttp.ClientSession, media_id: str) -> str:
    """Exact host path for a VuIO id. Prefix-swapped this IS CrateMind's track key,
    so the seed needs no searching or guessing by title."""
    try:
        data = await vuio_call(session, "get_media_info", {"file_id": int(media_id)})
    except Exception:  # ponytail: best-effort; title search stays the fallback
        return ""
    return data.get("path", "")


async def _resolve(session: aiohttp.ClientSession, path: str) -> Track | None:
    files = await _vuio_search(session, _basename(path))
    f = _match_file(files, path)
    if not f:
        return None
    return Track(
        # Untagged files carry null, not a missing key, so a .get default would
        # not fire and "None" would end up on screen and in the dedup key.
        id=str(f["id"]), title=f.get("title") or _crate_query(_basename(path), ""),
        artist=f.get("artist") or "", album=f.get("album") or "",
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


async def count_play(media_url: str, skipped: bool = False, title: str = "",
                     artist: str = "", album: str = "") -> bool:
    """Tell CrateMind this track was played (or skipped), so it feeds taste.

    False when CrateMind doesn't know the file — nothing to count against.
    """
    async with aiohttp.ClientSession(raise_for_status=False,
                                     timeout=aiohttp.ClientTimeout(total=15)) as s:
        path = await _crate_path_of(s, media_url, title, artist, album)
        if not path:
            return False
        async with s.post(f"{CRATE_URL}/api/plays",
                          json={"path": path, "skipped": skipped}) as r:
            if r.status == 404:
                return False
            r.raise_for_status()
    return True


async def rate(media_url: str, rating: int, title: str = "",
               artist: str = "", album: str = "") -> bool:
    """Tell CrateMind the user liked (+1) / banned (-1) / un-rated (0) a track.

    CrateMind keys tracks by path, so resolve the VuIO id in the stream URL to
    one the way radio does. Returns False when the file isn't one CrateMind
    analysed — there is nothing to rate then, and the caller should say so.
    """
    async with aiohttp.ClientSession(raise_for_status=False,
                                     timeout=aiohttp.ClientTimeout(total=15)) as s:
        path = await _crate_path_of(s, media_url, title, artist, album)
        if not path:
            return False
        async with s.put(f"{CRATE_URL}/api/ratings",
                         json={"path": path, "rating": rating}) as r:
            if r.status == 404:  # analysed by VuIO but not by CrateMind
                return False
            r.raise_for_status()
    return True


async def _crate_path_of(s: aiohttp.ClientSession, media_url: str, title: str,
                         artist: str, album: str) -> str:
    """This track's path as CrateMind knows it, or "" if it doesn't."""
    mid = _media_id(media_url)
    vuio_path = await _vuio_path(s, mid) if mid else ""
    async with s.get(f"{CRATE_URL}/api/tracks",
                     params={"q": _crate_query(_basename(vuio_path), title),
                             "limit": 20}) as r:
        r.raise_for_status()
        candidates = [c["path"] for c in (await r.json()).get("tracks", [])]
    exact = _best_match(candidates, vuio_path)
    if exact:
        return exact
    # No exact file: rating another copy of the same song is still right, since
    # taste is about the song. Ranked, so it is the most plausible copy.
    ranked = _rank_seeds([{"path": p} for p in candidates], artist, album)
    return ranked[0] if ranked else ""


async def radio_tracks(title: str, artist: str = "", limit: int = 10,
                       album: str = "", media_url: str = "") -> list[Track]:
    """Tracks similar to the given one, as playable Tracks (unresolved ones dropped)."""
    async with aiohttp.ClientSession(raise_for_status=False,
                                     timeout=aiohttp.ClientTimeout(total=15)) as s:
        # The DLNA link carries VuIO's id, which gives this file's real path.
        # CrateMind stores the same file under its own root, so the tail
        # identifies it exactly — no title guessing, no shared prefix config.
        mid = _media_id(media_url)
        vuio_path = await _vuio_path(s, mid) if mid else ""
        async with s.get(f"{CRATE_URL}/api/tracks",
                         params={"q": _crate_query(_basename(vuio_path), title),
                                 "limit": 20}) as r:
            r.raise_for_status()
            candidates = (await r.json()).get("tracks", [])
        exact = _best_match([c["path"] for c in candidates], vuio_path)
        # Fall back to other copies of the song (ranked) if CrateMind never
        # analysed this exact file; that seed 404s and yields nothing.
        seed, recs = None, []
        for cand in ([exact] if exact else []) + _rank_seeds(candidates, artist, album):
            # over-fetch: the seed and duplicate songs drop out below, and the
            # caller asked for `limit` tracks to play, not `limit` candidates
            recs = await _preview(s, cand, limit * 2)
            if recs:
                seed = cand
                break
        out = []
        seen = {song_key(artist, title, vuio_path or seed or "")}
        for rec in recs:
            if len(out) == limit:
                break
            if rec["path"] == seed:  # the seed itself; skip before resolving it
                continue
            t = await _resolve(s, rec["path"])
            if t and song_key(t.artist, t.title, rec["path"]) not in seen:
                seen.add(song_key(t.artist, t.title, rec["path"]))
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
    # deepest shared tail identifies a file across differently-mounted roots
    v = "/Volumes/Platte/Musik"
    assert _common_tail(v + "/A - Gold/01. x.flac", "/music/A - Gold/01. x.flac") == 2
    assert _best_match([v + "/Comp - Hits/01. x.flac", v + "/A - Gold/01. x.flac"],
                       "/music/A - Gold/01. x.flac").endswith("A - Gold/01. x.flac")
    # deeper nesting just raises the bar rather than reaching into the root
    assert _best_match([v + "/A/CD2/01. x.flac", v + "/A/CD1/01. x.flac"],
                       "/music/A/CD1/01. x.flac").endswith("CD1/01. x.flac")
    # filename alone is not enough, and a genuine tie stays unresolved
    assert _best_match([v + "/Other - Hits/01. x.flac"], "/music/A - Gold/01. x.flac") is None
    assert _best_match([v + "/A/01. x.flac", "/elsewhere/A/01. x.flac"],
                       "/music/A/01. x.flac") is None
    assert _best_match([v + "/A/01. x.flac"], "") is None
    # one song, one key: compilation copy, remaster and edit all collapse
    k = song_key("4 Non Blondes", "What's Up?")
    assert song_key("4 Non Blondes", "what's up?") == k
    assert song_key("The Cranberries", "The Icicle Melts (2025 Remastered)") \
        == song_key("The Cranberries", "The Icicle Melts")
    assert song_key("Madonna", "Crazy For You (Atmos Mix)") \
        == song_key("Madonna", "Crazy for You (Edit)")
    assert song_key("", "", "/music/A - Gold/03. 4 Non Blondes - What's Up.m4a") \
        == song_key("4 Non Blondes", "What's Up")
    assert song_key("ABBA", "Head Over Heels") != k
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
    # untagged file: no "None" artist, and the fallback title loses number+suffix
    assert _crate_query("08 - This Is The Life (Live).flac", "") == "This Is The Life (Live)"
    assert song_key(None or "", "x") == song_key("", "x")
    print("ok")


if __name__ == "__main__":
    _selfcheck()
