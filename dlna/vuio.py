"""Talking to VuIO over its MCP endpoint, and handing playback over to it.

VuIO serves the same files this app browses and can drive a renderer itself.
Pushing the queue across as a VuIO playlist means the music keeps going once
this app exits: from then on VuIO advances the tracks, not us.
"""
from __future__ import annotations

import json
import os

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
    return result.get("structuredContent") or json.loads(result["content"][0]["text"])


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


async def handoff(tracks, renderer_id: str, index: int = 0,
                  name: str = "dlna-tui") -> int:
    """Put `tracks` into a VuIO playlist and cast it from `index`.

    Returns the number of tracks handed over. Raises if VuIO rejects a step —
    the caller must not report a handoff that didn't happen.
    """
    ids = media_ids(tracks)
    if not ids:
        return 0
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
        created = await call(s, "create_playlist",
                             {"name": name, "description": "handed over from dlna-tui"})
        pid = created["playlist_id"]
        await call(s, "add_to_playlist", {"playlist_id": pid, "media_file_ids": ids})
        await call(s, "cast_playlist_to_renderer",
                   {"playlist_id": pid, "renderer_id": renderer_id,
                    "track_index": index})
    return len(ids)


def _selfcheck() -> None:
    class T:
        def __init__(self, i):
            self.id = i

    assert media_ids([T("43950"), T("7")]) == [43950, 7]
    assert media_ids([]) == []
    assert media_ids([T("43950"), T("i1")]) is None  # non-VuIO track -> refuse
    print("ok")


if __name__ == "__main__":
    _selfcheck()
