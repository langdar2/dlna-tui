import asyncio
from io import BytesIO

from PIL import Image

from dlna import display
from dlna.display import (SIZE, DisplayState, PixelDisplay, cover_frame,
                          progress_columns, scroll_frames)


def _png(size, colour):
    buf = BytesIO()
    Image.new("RGB", size, colour).save(buf, format="PNG")
    return buf.getvalue()


def test_progress_columns_clamps_and_handles_unknown_length():
    assert progress_columns(0, 100) == 0
    assert progress_columns(50, 100) == SIZE // 2
    assert progress_columns(100, 100) == SIZE
    assert progress_columns(500, 100) == SIZE      # past the end
    assert progress_columns(-5, 100) == 0
    assert progress_columns(10, 0) == 0            # m4a: no length known


def test_cover_frame_is_32x32_and_bar_fills_from_the_left():
    img = cover_frame(_png((300, 200), (200, 0, 0)), lit=8)
    assert img.size == (SIZE, SIZE)
    y = SIZE - 1
    assert img.getpixel((0, y)) == display.BAR_FG
    assert img.getpixel((7, y)) == display.BAR_FG
    assert img.getpixel((8, y)) == display.BAR_BG
    assert img.getpixel((SIZE - 1, y)) == display.BAR_BG
    assert img.getpixel((16, 5))[0] > 150           # cover colour survives above the bar


def test_non_square_cover_is_cropped_not_squashed():
    wide = Image.new("RGB", (400, 100), (0, 0, 255))
    ImageDrawer = __import__("PIL.ImageDraw", fromlist=["x"])
    ImageDrawer.Draw(wide).rectangle((0, 0, 99, 99), fill=(255, 0, 0))   # left square red
    buf = BytesIO(); wide.save(buf, format="PNG")
    img = cover_frame(buf.getvalue(), lit=0)
    # a centred crop of the middle must be blue; squashing would show red at the left
    assert img.getpixel((2, 10))[2] > 200 and img.getpixel((2, 10))[0] < 50


def test_missing_or_broken_cover_gives_a_plain_tile_not_an_error():
    for bad in (None, b"", b"not an image"):
        img = cover_frame(bad, lit=SIZE)
        assert img.size == (SIZE, SIZE)
        assert img.getpixel((SIZE - 1, SIZE - 1)) == display.BAR_FG


def test_scroll_runs_the_text_all_the_way_across():
    frames = scroll_frames("A fairly long track title - Some Artist")
    assert all(f.size == (SIZE, SIZE) for f in frames)
    assert len(frames) > SIZE // 2
    assert not frames[0].getbbox() or frames[0].getbbox()[2] <= SIZE   # starts off-screen
    assert frames[0].convert("L").getextrema()[1] == 0                  # first frame empty
    assert any(f.convert("L").getextrema()[1] > 0 for f in frames)       # text is visible
    assert frames[-1].convert("L").getextrema()[1] == 0                  # leaves entirely


def test_state_scrolls_once_per_track_then_only_when_the_bar_moves():
    st = DisplayState()
    assert st.decide("t1", "Title", "Artist", 0, 100) == ("scroll", "Title - Artist")
    assert st.decide("t1", "Title", "Artist", 0, 100) == ("cover", 0)
    assert st.decide("t1", "Title", "Artist", 0.5, 100) is None        # same column
    assert st.decide("t1", "Title", "Artist", 10, 100) == ("cover", 3)
    assert st.decide("t1", "Title", "Artist", 10, 100) is None         # nothing changed
    assert st.decide("t2", "Next", "Band", 0, 100) == ("scroll", "Next - Band")


def test_state_does_not_scroll_an_empty_title():
    st = DisplayState()
    assert st.decide("t1", "", "", 0, 100) == ("cover", 0)


def test_a_disabled_display_is_inert(monkeypatch):
    monkeypatch.delenv("DLNA_TUI_IDM", raising=False)
    assert display.get_display() is None


async def test_update_without_hardware_never_raises_and_reports_why(monkeypatch):
    d = PixelDisplay("00000000-0000-0000-0000-000000000000")

    async def no_device():
        raise RuntimeError("display not found or not connectable")

    monkeypatch.setattr(d, "connect", lambda: asyncio.sleep(0, result=False))
    await d.update("t1", "Title", "Artist", 0, 100, b"")   # must not raise
    # nothing was sent, and the next change can retry
    assert d._connected is False


async def test_overlapping_updates_skip_instead_of_queueing(monkeypatch):
    d = PixelDisplay("x")
    sent = []

    async def slow_connect():
        d._connected = True
        return True

    async def slow_send(img):
        sent.append(1)
        await asyncio.sleep(0.05)

    monkeypatch.setattr(d, "connect", slow_connect)
    monkeypatch.setattr(d, "_send_png", slow_send)
    monkeypatch.setattr(d, "_send_gif", slow_send)
    await asyncio.gather(*(d.update("t", "T", "A", i, 100) for i in range(5)))
    assert len(sent) < 5      # ticks arriving mid-upload were dropped, not stacked


def test_a_long_title_cannot_blow_up_the_bluetooth_upload():
    """Frames are uploaded over BLE; an uncapped 120-char title was ~175 KB."""
    from dlna.display import MAX_SCROLL_CHARS, MAX_SCROLL_FRAMES
    frames = scroll_frames("x" * 500)
    assert len(frames) <= MAX_SCROLL_FRAMES + 1
    short = scroll_frames("Intro")
    assert len(short) <= MAX_SCROLL_FRAMES
    # a short title keeps its smooth step instead of being thinned out
    assert len(short) > 20
    assert MAX_SCROLL_CHARS < 100
