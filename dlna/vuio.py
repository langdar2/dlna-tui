"""Talking to VuIO over its MCP endpoint, and handing playback over to it.

VuIO serves the same files this app browses and can drive a renderer itself.
Pushing the queue across as a VuIO playlist means the music keeps going once
this app exits: from then on VuIO advances the tracks, not us.
"""
from __future__ import annotations

import asyncio
import json
import os
from urllib.parse import urlparse

import aiohttp

VUIO_URL = os.environ.get("VUIO_URL", "http://192.168.0.3:8080")
_MCP_VERSION = "2026-07-28"


async def call(session: aiohttp.ClientSession, tool: str, args: dict) -> dict:
    """Invoke one VuIO MCP tool over HTTP and return its parsed result."""
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
    if "error" in payload:
        raise RuntimeError(f"VuIO {tool}: {payload['error']}")
    result = payload["result"]
    if result.get("structuredContent"):
        return result["structuredContent"]
    text = (result.get("content") or [{}])[0].get("text", "")
    try:
        return json.loads(text)
    except ValueError:  # say what came back; a bare JSONDecodeError names no tool
        raise RuntimeError(f"VuIO {tool}: unreadable reply {text[:200]!r}") from None


def media_ids(tracks) -> list[int] | None:
    """Queue as VuIO file ids, or None if any track isn't one of VuIO's.

    A DLNA object id from this server IS the VuIO media id, so normally every
    track maps straight across. Refuse the whole batch rather than silently
    drop entries: a hole would shift the start index and play the wrong song.
    """
    ids = []
    for t in tracks:
        if not str(t.id).isdigit():
            return None
        ids.append(int(t.id))
    return ids


# One box is usually published over several protocols. Measured on a Cambridge
# Evo One: over chromecast VuIO walks a playlist in order, over dlna it jumps
# around and repeats (observed 0,4,3,4,2,3,4 for a five-track list), so prefer
# chromecast for the handoff even though this app itself talks DLNA.
_PROTOCOL_RANK = {"chromecast": 0, "dlna": 1, "airplay": 2}


async def pick_renderer(session: aiohttp.ClientSession, udn: str,
                        location: str = "") -> str:
    """VuIO's best id for the renderer this app is playing to."""
    host = urlparse(location).hostname if location else None
    found = (await call(session, "list_renderers", {})).get("renderers", [])
    same = [r for r in found
            if r.get("id") == udn
            or (host and urlparse(r.get("location") or "").hostname == host)]
    if not same:
        return udn
    same.sort(key=lambda r: _PROTOCOL_RANK.get(r.get("protocol"), 9))
    return same[0]["id"]


async def handoff(tracks, udn: str, location: str = "", index: int = 0,
                  name: str = "dlna-tui") -> tuple[int, str]:
    """Put `tracks` into a VuIO playlist and cast it from `index`.

    Returns (tracks handed over, protocol used). Raises if VuIO rejects a
    step — the caller must not report a handoff that didn't happen.
    """
    ids = media_ids(tracks)
    if not ids:
        return 0, ""
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
        target = await pick_renderer(s, udn, location)
        if target != udn:
            # Chromecast won't launch while the box is still streaming over
            # DLNA ("application launch failed: CANCELLED"), so let go first.
            try:
                await call(s, "control_renderer", {"renderer_id": udn, "action": "stop"})
            except Exception:
                pass  # already idle, or VuIO doesn't track it; the cast decides
            await asyncio.sleep(2)  # the device needs a moment to free the session
        created = await call(s, "create_playlist",
                             {"name": name, "description": "handed over from dlna-tui"})
        pid = created["playlist_id"]
        await call(s, "add_to_playlist", {"playlist_id": pid, "media_file_ids": ids})
        await call(s, "cast_playlist_to_renderer",
                   {"playlist_id": pid, "renderer_id": target,
                    "track_index": index})
    return len(ids), target.split(":", 1)[0]


def _selfcheck() -> None:
    class T:
        def __init__(self, i):
            self.id = i

    assert media_ids([T("43950"), T("7")]) == [43950, 7]
    assert media_ids([]) == []
    assert media_ids([T("43950"), T("i1")]) is None  # non-VuIO track -> refuse

    # same box over three protocols -> chromecast wins; a stranger is ignored
    found = {"renderers": [
        {"id": "uuid:evo", "protocol": "dlna",
         "location": "http://192.168.0.23:8050/x/description.xml"},
        {"id": "airplay:aa", "protocol": "airplay", "location": "airplay://192.168.0.23:7000"},
        {"id": "chromecast:cc", "protocol": "chromecast", "location": "cast://192.168.0.23:8009"},
        {"id": "chromecast:other", "protocol": "chromecast", "location": "cast://192.168.0.99:8009"},
    ]}

    async def fake_call(_s, _tool, _args):
        return found

    import asyncio as _a
    global call
    real, call = call, fake_call
    try:
        loc = "http://192.168.0.23:8050/x/description.xml"
        assert _a.run(pick_renderer(None, "uuid:evo", loc)) == "chromecast:cc"
        # unknown device -> fall back to the id we already have
        assert _a.run(pick_renderer(None, "uuid:nope", "http://10.0.0.1:1/d.xml")) == "uuid:nope"
        # no location: still matched by id, and dlna is all there is for it
        assert _a.run(pick_renderer(None, "airplay:aa", "")) == "airplay:aa"
    finally:
        call = real
    print("ok")


if __name__ == "__main__":
    _selfcheck()
