"""iDotMatrix 32x32 LED display: cover art, progress bar, scrolling title.

Optional. Enabled by DLNA_TUI_IDM=<name or address>; without it, or without
the idotmatrix package, everything here is a silent no-op.

The display is Bluetooth LE and the idotmatrix library only takes image
files, so every frame is rendered with Pillow into a temp file and uploaded.
Uploads are slow relative to a one-second UI tick, so DisplayState decides
*whether* anything changed and the driver only sends on a change.

Layout: the cover fills the 32x32 grid with the bottom row as a progress bar.
When the track changes, title and artist scroll past once, then the cover
returns.
"""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

SIZE = 32
BAR_ROWS = 2               # bottom rows used by the progress bar
BAR_FG = (0, 200, 90)
BAR_BG = (25, 25, 25)
# Progress is redrawn in coarse steps: 32 columns is all the resolution there
# is, so a finer update would upload identical frames.
PROGRESS_STEPS = SIZE

_FONT_CANDIDATES = (
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def _font(size: int) -> ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def progress_columns(position: float, duration: float) -> int:
    """Lit columns of the bar, 0..SIZE; 0 when the length is unknown."""
    if duration <= 0:
        return 0
    return max(0, min(SIZE, int(position / duration * SIZE)))


def cover_frame(cover: bytes | None, lit: int) -> Image.Image:
    """32x32 frame: cover (or a dark tile) with the progress bar on the bottom."""
    if cover:
        try:
            img = Image.open(BytesIO(cover)).convert("RGB")
            # Crop to a centred square first, so a non-square cover is cut,
            # not squashed.
            side = min(img.size)
            left, top = (img.width - side) // 2, (img.height - side) // 2
            img = img.crop((left, top, left + side, top + side))
            img = img.resize((SIZE, SIZE), Image.LANCZOS)
        except Exception:  # undecodable image: fall back to the plain tile
            img = Image.new("RGB", (SIZE, SIZE), (20, 20, 30))
    else:
        img = Image.new("RGB", (SIZE, SIZE), (20, 20, 30))
    draw = ImageDraw.Draw(img)
    y0 = SIZE - BAR_ROWS
    draw.rectangle((0, y0, SIZE - 1, SIZE - 1), fill=BAR_BG)
    if lit > 0:
        draw.rectangle((0, y0, lit - 1, SIZE - 1), fill=BAR_FG)
    return img


# A scrolling GIF is uploaded over Bluetooth LE, a few KB per second, and the
# frames cost about 0.4 KB each. Uncapped, a long title meant a 125-175 KB
# upload and half a minute of waiting before it even started to scroll. Cap
# the frame count (the step grows to fit) and the text length instead.
MAX_SCROLL_FRAMES = 110
MAX_SCROLL_CHARS = 40


def _shorten(text: str) -> str:
    return text if len(text) <= MAX_SCROLL_CHARS else text[:MAX_SCROLL_CHARS - 1] + "…"


def scroll_frames(text: str, colour=(255, 200, 0), step: int = 2) -> list[Image.Image]:
    """Frames of `text` scrolling right to left across the 32x32 grid.

    One line, vertically centred; the text enters from the right edge and
    leaves past the left, so a short title still crosses the whole display.
    `step` is the pixels moved per frame and is raised when the text is long
    enough that it would exceed MAX_SCROLL_FRAMES.
    """
    text = _shorten(text)
    font = _font(14)
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), text, font=font)
    width, height = right - left, bottom - top
    travel = width + SIZE
    step = max(step, -(-travel // MAX_SCROLL_FRAMES))  # ceil: stay under the cap
    strip = Image.new("RGB", (SIZE + width + SIZE, SIZE), (0, 0, 0))
    ImageDraw.Draw(strip).text((SIZE - left, (SIZE - height) // 2 - top), text,
                               fill=colour, font=font)
    return [strip.crop((x, 0, x + SIZE, SIZE))
            for x in range(0, travel + 1, step)]


@dataclass
class DisplayState:
    """What is on the display, so only real changes are sent.

    Pure logic with no Bluetooth: decide() says what to send for the current
    playback, or None when the display already shows it.
    """
    track_key: object = None
    lit: int = -1
    shown_scroll: bool = False
    pending: list = field(default_factory=list)

    def decide(self, track_key, title: str, artist: str,
               position: float, duration: float):
        """("scroll", text) on a new track, ("cover", lit) when the bar moved,
        else None."""
        lit = progress_columns(position, duration)
        if track_key != self.track_key:
            self.track_key, self.lit = track_key, -1
            self.shown_scroll = False
        if not self.shown_scroll:
            self.shown_scroll = True
            text = " - ".join(p for p in (title, artist) if p)
            if text:
                return ("scroll", text)
        if lit != self.lit:
            self.lit = lit
            return ("cover", lit)
        return None


class PixelDisplay:
    """Thin async wrapper over the idotmatrix library; never raises."""

    def __init__(self, target: str = "", brightness: int = 40):
        self.target = target
        self.brightness = max(5, min(100, brightness))
        self._connected = False
        self._lib = None
        self._cover: bytes | None = None
        self._cover_key: object = None
        self._lock = asyncio.Lock()
        self.state = DisplayState()
        self.last_error = ""

    # -- availability -----------------------------------------------------
    def is_available(self) -> bool:
        return bool(self.target)

    def _import(self):
        if self._lib is None:
            from idotmatrix import Common, ConnectionManager, Gif, Image as Img
            self._lib = (Common, ConnectionManager, Gif, Img)
        return self._lib

    async def connect(self) -> bool:
        if self._connected:
            return True
        try:
            Common, ConnectionManager, _, _ = self._import()
            mgr = ConnectionManager()
            if mgr is None:
                raise RuntimeError("idotmatrix connection manager unavailable")
            if self.target.upper().startswith("IDM-") or self.target == "auto":
                await mgr.connectBySearch()
            else:
                await mgr.connectByAddress(self.target)
            if not (mgr.client and mgr.client.is_connected):
                raise RuntimeError("display not found or not connectable")
            await Common().setBrightness(self.brightness)
            self._connected = True
            self.last_error = ""
        except Exception as exc:
            self.last_error = str(exc)
            log.warning("iDotMatrix: %s", exc)
            self._connected = False
        return self._connected

    async def close(self, blank: bool = True) -> None:
        """Release the display; optionally switch it off rather than leave the
        last frame glowing after the app is gone."""
        if not self._connected:
            return
        try:
            Common, ConnectionManager, _, _ = self._import()
            if blank:
                await Common().screenOff()
            await ConnectionManager().disconnect()
        except Exception as exc:
            log.debug("iDotMatrix close: %s", exc)
        finally:
            self._connected = False

    # -- drawing ----------------------------------------------------------
    async def _send_png(self, img: Image.Image) -> None:
        _, _, _, Img = self._import()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frame.png"
            img.save(path, format="PNG")
            await Img().setMode(1)
            await Img().uploadProcessed(str(path), pixel_size=SIZE)

    async def _send_gif(self, frames: list[Image.Image], ms: int = 70) -> None:
        _, _, Gif, _ = self._import()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scroll.gif"
            frames[0].save(path, format="GIF", save_all=True,
                           append_images=frames[1:], duration=ms, loop=0)
            await Gif().uploadProcessed(str(path), pixel_size=SIZE)

    async def update(self, track_key, title: str, artist: str, position: float,
                     duration: float, cover: bytes | None = None) -> None:
        """Show what is playing; sends only when something visibly changed."""
        if not self.is_available():
            return
        if self._lock.locked():  # previous upload still running; skip this tick
            return
        async with self._lock:
            if cover is not None and track_key != self._cover_key:
                self._cover, self._cover_key = cover, track_key
            action = self.state.decide(track_key, title, artist, position, duration)
            if action is None:
                return
            if not await self.connect():
                return
            try:
                kind, value = action
                if kind == "scroll":
                    await self._send_gif(scroll_frames(value))
                else:
                    await self._send_png(cover_frame(self._cover, value))
            except Exception as exc:
                self.last_error = str(exc)
                log.warning("iDotMatrix update failed: %s", exc)
                self._connected = False  # reconnect on the next change


_INSTANCE: PixelDisplay | None = None


def get_display() -> PixelDisplay | None:
    """The display named by DLNA_TUI_IDM, or None when not configured.

    DLNA_TUI_IDM is the device's name (IDM-xxxxxx), its address (a UUID on
    macOS, a MAC elsewhere), or "auto" to use the first one found.
    """
    global _INSTANCE
    target = os.environ.get("DLNA_TUI_IDM", "").strip()
    if not target:
        return None
    try:
        import idotmatrix  # noqa: F401
    except ImportError:
        log.warning("DLNA_TUI_IDM is set but 'idotmatrix' is not installed "
                    "(pip install idotmatrix)")
        return None
    if _INSTANCE is None:
        _INSTANCE = PixelDisplay(target)
    return _INSTANCE
