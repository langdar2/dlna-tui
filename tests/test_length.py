import asyncio
import struct

from dlna import length
from dlna.models import Queue, Track
from dlna.renderer import RendererState
from ui import app as app_mod
from ui.app import DlnaApp


def _box(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(body), kind) + body


def _mvhd(timescale: int, duration: int) -> bytes:
    return _box(b"mvhd", bytes(4) + bytes(8) + struct.pack(">II", timescale, duration) + bytes(80))


def _flac_moov(rate: int, total: int, mvhd_duration: int = 0) -> bytes:
    packed = (rate << 44) | (1 << 41) | (23 << 36) | total       # 2 channels, 24 bit
    streaminfo = bytes(10) + packed.to_bytes(8, "big") + bytes(16)
    dfla = _box(b"dfLa", bytes(4) + bytes([0x80, 0, 0, 34]) + streaminfo)
    return _box(b"moov", _mvhd(rate, mvhd_duration) + _box(b"trak", dfla))


def test_length_comes_from_the_container_when_it_has_one():
    moov = _box(b"moov", _mvhd(1000, 201_407))
    assert round(length.seconds_from_header(moov), 1) == 201.4


def test_flac_in_mp4_with_a_zero_container_length_uses_the_flac_header():
    """The real case: mvhd is 0 because the file is fragmented, but the FLAC
    STREAMINFO inside carries the sample count."""
    moov = _flac_moov(rate=96000, total=28_189_440, mvhd_duration=0)
    assert round(length.seconds_from_header(moov), 1) == 293.6


def test_unknown_layouts_give_no_length_instead_of_a_wrong_one():
    assert length.seconds_from_header(_box(b"moov", _mvhd(1000, 0))) == 0
    assert length.seconds_from_header(b"") == 0
    assert length.seconds_from_header(_flac_moov(44100, 0)) == 0   # total unknown


def test_an_unreachable_file_means_no_length_not_an_error():
    assert length.mp4_seconds("http://127.0.0.1:9/none.m4a") == 0


class _R:
    def __init__(self):
        self.pos = 0

    def state(self):
        return RendererState(transport_state="PLAYING", position=self.pos, duration=0)

    async def update(self):
        return True


class _App(DlnaApp):
    async def on_mount(self):
        pass


async def test_a_missing_length_is_looked_up_once_and_reaches_the_title_bar(monkeypatch):
    calls = []
    monkeypatch.setattr(app_mod, "mp4_seconds", lambda url: calls.append(url) or 293)
    a = _App(store=None, requester=None, event_handler=None)
    async with a.run_test() as pilot:
        a.renderer = _R()
        a.queue = Queue([Track(id="1", title="What's Up?", media_url="http://h/1.m4a")])
        for _ in range(4):
            await a._poll()
            await pilot.pause()
            await asyncio.sleep(0.05)
        assert calls == ["http://h/1.m4a"]              # asked once, not every tick
        assert a.queue.current().duration == "0:04:53"
        assert a.query_one("#now").st.duration == 293   # what the title bar shows


async def test_a_length_the_server_already_gave_is_not_fetched(monkeypatch):
    monkeypatch.setattr(app_mod, "mp4_seconds",
                        lambda url: (_ for _ in ()).throw(AssertionError("must not fetch")))
    a = _App(store=None, requester=None, event_handler=None)
    async with a.run_test() as pilot:
        a.renderer = _R()
        a.queue = Queue([Track(id="1", title="Song", media_url="http://h/1.flac",
                               duration="0:03:00")])
        await a._poll()
        await pilot.pause()
        assert a.query_one("#now").st.duration == 180


async def test_a_failed_lookup_is_not_retried_every_second(monkeypatch):
    calls = []
    monkeypatch.setattr(app_mod, "mp4_seconds", lambda url: calls.append(1) or 0)
    a = _App(store=None, requester=None, event_handler=None)
    async with a.run_test() as pilot:
        a.renderer = _R()
        a.queue = Queue([Track(id="1", title="Odd", media_url="http://h/1.m4a")])
        for _ in range(5):
            await a._poll()
            await pilot.pause()
            await asyncio.sleep(0.05)
        assert len(calls) == 1


async def test_a_long_m4a_now_needs_half_its_length_to_count_as_played(monkeypatch):
    """The point of the lookup: the threshold stops falling back to 30 s."""
    from ui.app import play_threshold
    monkeypatch.setattr(app_mod, "mp4_seconds", lambda url: 360)
    a = _App(store=None, requester=None, event_handler=None)
    async with a.run_test() as pilot:
        a.renderer = _R()
        a.queue = Queue([Track(id="1", title="Long", media_url="http://h/1.m4a")])
        await a._poll()
        await pilot.pause()
        await asyncio.sleep(0.05)
        assert play_threshold(app_mod._hms_seconds(a.queue.current().duration)) == 180
