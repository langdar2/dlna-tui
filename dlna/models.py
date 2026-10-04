from __future__ import annotations

from dataclasses import dataclass, field
from didl_lite import didl_lite


@dataclass
class DeviceInfo:
    udn: str
    name: str
    location: str
    kind: str  # "server" | "renderer"


@dataclass
class Container:
    id: str
    title: str
    child_count: int | None = None


@dataclass
class Track:
    id: str
    title: str
    artist: str = ""
    album: str = ""
    duration: str = ""
    media_url: str = ""
    didl: str = ""  # DIDL-Lite fragment for the renderer
    info: str = ""  # human-readable media summary (type, rate, size, …)
    art_uri: str = ""  # albumArtURI, if the server provides one


def _first_res(obj):
    for res in getattr(obj, "res", []) or []:
        if getattr(res, "uri", None):
            return res
    return None


def _first_res_uri(obj) -> str:
    res = _first_res(obj)
    return res.uri if res else ""


def _first_res_duration(obj) -> str:
    for res in getattr(obj, "res", []) or []:
        if getattr(res, "duration", None):
            return res.duration
    return ""


def _media_info(obj) -> str:
    """Summarise the first <res>: file type, sample rate, depth, channels, size."""
    res = _first_res(obj)
    if res is None:
        return ""
    parts: list[str] = []
    # protocolInfo looks like "http-get:*:audio/flac:*" -> take the subtype.
    # Fall back to the URL's file extension when the server omits it.
    pi = getattr(res, "protocol_info", "") or ""
    fields = pi.split(":")
    if len(fields) >= 3 and "/" in fields[2]:
        parts.append(fields[2].split("/")[-1])
    elif "." in (res.uri or "").rsplit("/", 1)[-1]:
        parts.append(res.uri.rsplit(".", 1)[-1].split("?")[0].lower())
    freq = getattr(res, "sample_frequency", None)
    if freq:
        parts.append(f"{int(freq) / 1000:g}kHz")
    depth = getattr(res, "bits_per_sample", None)
    if depth:
        parts.append(f"{depth}bit")
    ch = getattr(res, "nr_audio_channels", None)
    if ch:
        parts.append(f"{ch}ch")
    size = getattr(res, "size", None)
    if size:
        parts.append(f"{int(size) / 1_048_576:.1f} MB")
    return " · ".join(parts)


def _to_model(obj):
    if isinstance(obj, didl_lite.Container):
        cc = obj.child_count
        return Container(
            id=obj.id,
            title=obj.title or "",
            child_count=int(cc) if cc not in (None, "") else None,
        )
    return Track(
        id=obj.id,
        title=obj.title or "",
        artist=getattr(obj, "artist", "") or "",
        album=getattr(obj, "album", "") or "",
        duration=_first_res_duration(obj),
        media_url=_first_res_uri(obj),
        didl=didl_lite.to_xml_string(obj).decode(),
        info=_media_info(obj),
        art_uri=getattr(obj, "album_art_uri", "") or "",
    )


@dataclass
class Queue:
    tracks: list[Track] = field(default_factory=list)
    index: int = 0

    def current(self) -> Track | None:
        if 0 <= self.index < len(self.tracks):
            return self.tracks[self.index]
        return None

    def advance(self) -> Track | None:
        if self.index + 1 < len(self.tracks):
            self.index += 1
            return self.tracks[self.index]
        return None

    def prev(self) -> Track | None:
        if self.index > 0:
            self.index -= 1
            return self.tracks[self.index]
        return None

    def append(self, track: Track) -> None:
        self.tracks.append(track)

    def drop_after_current(self) -> None:
        """Forget what's queued behind the current track, keeping it playing.
        Switching to radio uses this so suggestions play next instead of after
        the rest of the album the folder happened to queue."""
        del self.tracks[self.index + 1:]


def _is_audio(obj) -> bool:
    # upnp:class e.g. "object.item.audioItem.musicTrack". Video/image items are
    # dropped; this is a music client.
    return "audioitem" in (getattr(obj, "upnp_class", "") or "").lower()


def to_models(objs) -> list[Container | Track]:
    """Already-parsed didl_lite objects -> our models (Descriptors dropped).

    Containers are kept for navigation; only audio items pass through.
    ponytail: a video-only container still shows (empty); hiding it would need
    browsing it first. Acceptable clutter — revisit if libraries are mixed-heavy.
    """
    return [_to_model(o) for o in objs
            if isinstance(o, didl_lite.Container)
            or (isinstance(o, didl_lite.Item) and _is_audio(o))]


def from_didl(didl_xml: str) -> list[Container | Track]:
    """DIDL-Lite XML -> list of our models (Descriptors dropped)."""
    return to_models(didl_lite.from_xml_string(didl_xml, strict=False))
