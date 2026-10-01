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


def _first_res_uri(obj) -> str:
    for res in getattr(obj, "res", []) or []:
        if getattr(res, "uri", None):
            return res.uri
    return ""


def _first_res_duration(obj) -> str:
    for res in getattr(obj, "res", []) or []:
        if getattr(res, "duration", None):
            return res.duration
    return ""


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


def from_didl(didl_xml: str) -> list[Container | Track]:
    """DIDL-Lite XML -> list of our models (Descriptors dropped)."""
    out: list[Container | Track] = []
    for obj in didl_lite.from_xml_string(didl_xml, strict=False):
        if isinstance(obj, (didl_lite.Container, didl_lite.Item)):
            out.append(_to_model(obj))
    return out
