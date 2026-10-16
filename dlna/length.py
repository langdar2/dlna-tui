"""Track length read from the file itself, for when the server does not know it.

VuIO reports no duration for m4a, and the renderer then reports none over
UPnP either, although it shows the right length on its own display. Measured on
228 m4a files: the container's own length field (mvhd) is 0, because these are
FLAC streams wrapped in fragmented MP4, but the FLAC STREAMINFO block inside
the header holds the sample count and rate, which is all a length needs.

Only the first few hundred KB are fetched (the header comes before the audio),
so this costs one small Range request per track, once.
"""
from __future__ import annotations

import struct
import urllib.request

_HEAD = 64                 # enough to find the first top-level boxes
_MAX_MOOV = 400_000        # the header holds embedded cover art, ~160 KB seen


def _range(url: str, start: int, end: int, timeout: float = 15) -> bytes:
    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _top_level(buf: bytes):
    """(type, offset, size) of the MP4 boxes at the start of `buf`."""
    off = 0
    while off + 8 <= len(buf):
        size, kind = struct.unpack(">I4s", buf[off:off + 8])
        if size == 1 and off + 16 <= len(buf):
            size = struct.unpack(">Q", buf[off + 8:off + 16])[0]
        if size < 8:
            return
        yield kind, off, size
        off += size


def _header_time(moov: bytes, box: bytes) -> float:
    """Seconds from an mvhd/mdhd box inside `moov`; 0 when absent or zero."""
    i = moov.find(box)
    if i < 0:
        return 0.0
    body = i + 4                       # after the 4-char type: version, flags, ...
    version = moov[body]
    if version == 1:
        timescale, duration = struct.unpack(">IQ", moov[body + 20:body + 32])
    else:
        timescale, duration = struct.unpack(">II", moov[body + 12:body + 20])
    return duration / timescale if timescale and duration else 0.0


def _flac_seconds(moov: bytes) -> float:
    """Length from the FLAC STREAMINFO block (sample rate, total samples)."""
    i = moov.find(b"dfLa")
    if i < 0:
        return 0.0
    block = moov[i + 8:]               # skip 'dfLa' and its version/flags
    if len(block) < 4 + 18 or block[0] & 0x7F != 0:   # first block must be STREAMINFO
        return 0.0
    packed = int.from_bytes(block[4 + 10:4 + 18], "big")
    rate, total = packed >> 44, packed & ((1 << 36) - 1)
    return total / rate if rate and total else 0.0


def seconds_from_header(moov: bytes) -> float:
    """Best length found in an MP4 `moov` box: container first, then FLAC."""
    return (_header_time(moov, b"mvhd") or _flac_seconds(moov)
            or _header_time(moov, b"mdhd"))


def mp4_seconds(url: str) -> int:
    """Length of an MP4/M4A at `url` in whole seconds, 0 if it cannot be told.

    Blocking; call it from a thread. Never raises: an unreachable file or an
    unfamiliar layout just means no length, as before.
    """
    try:
        head = _range(url, 0, _HEAD - 1)
        for kind, off, size in _top_level(head):
            if kind == b"moov":
                moov = _range(url, off, off + min(size, _MAX_MOOV) - 1)
                return int(seconds_from_header(moov))
    except Exception:
        pass
    return 0
