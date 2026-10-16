import asyncio

from dlna.models import Queue, Track
from dlna.renderer import RendererState
from ui import app as app_mod
from ui.app import PLAY_THRESHOLD_SECONDS, DlnaApp


class FakeRenderer:
    def __init__(self):
        self.st = RendererState(transport_state="PLAYING")

    def state(self):
        return self.st


def _app(monkeypatch):
    reported = []

    async def fake_count(media_url, skipped=False, title="", artist="", album=""):
        reported.append((title, skipped))
        return True

    monkeypatch.setattr(app_mod, "count_play", fake_count)
    a = DlnaApp(store=None, requester=None, event_handler=None)
    a.renderer = FakeRenderer()
    a.queue = Queue([Track(id="1", title="A"), Track(id="2", title="B")])
    return a, reported


async def _listen(a, seconds):
    for _ in range(seconds):
        a._tick_play_time()
    await asyncio.sleep(0)  # let the spawned report tasks run


async def test_play_counts_once_past_the_threshold(monkeypatch):
    a, reported = _app(monkeypatch)

    await _listen(a, PLAY_THRESHOLD_SECONDS - 1)
    assert reported == []  # too early to call it a play

    await _listen(a, 1)
    assert reported == [("A", False)]

    await _listen(a, 60)  # a long track still counts exactly once
    assert reported == [("A", False)]


async def test_skipping_early_reports_a_skip_not_a_play(monkeypatch):
    a, reported = _app(monkeypatch)

    await _listen(a, 5)
    a.queue.advance()          # user hits 'n'
    a._tick_play_time()
    await asyncio.sleep(0)
    assert reported == [("A", True)]

    await _listen(a, PLAY_THRESHOLD_SECONDS)
    assert reported == [("A", True), ("B", False)]


async def test_moving_on_after_a_full_listen_is_not_a_skip(monkeypatch):
    a, reported = _app(monkeypatch)

    await _listen(a, PLAY_THRESHOLD_SECONDS + 5)
    a.queue.advance()
    a._tick_play_time()
    await asyncio.sleep(0)
    assert reported == [("A", False)]  # no skip for the track just finished


async def test_paused_and_handed_off_playback_does_not_accrue(monkeypatch):
    a, reported = _app(monkeypatch)

    a.renderer.st = RendererState(transport_state="PAUSED_PLAYBACK")
    await _listen(a, PLAY_THRESHOLD_SECONDS * 2)
    assert reported == []

    a.renderer.st = RendererState(transport_state="PLAYING")
    a.handed_off = True        # VuIO is driving; it counts its own plays
    await _listen(a, PLAY_THRESHOLD_SECONDS * 2)
    assert reported == []


async def test_replaying_the_same_track_counts_again(monkeypatch):
    a, reported = _app(monkeypatch)

    await _listen(a, PLAY_THRESHOLD_SECONDS)
    a.queue.advance()
    await _listen(a, PLAY_THRESHOLD_SECONDS)
    a.queue.index = 0          # back to A, e.g. via 'p'
    await _listen(a, PLAY_THRESHOLD_SECONDS)

    assert reported == [("A", False), ("B", False), ("A", False)]


def test_threshold_follows_the_scrobble_rule():
    from ui.app import play_threshold
    assert play_threshold(0) == 30          # no duration (m4a): flat fallback
    assert play_threshold(360) == 180       # 6 min: half the track
    assert play_threshold(600) == 240       # 10 min: capped at 4 min
    assert play_threshold(90) == 45
    assert play_threshold(30) is None       # too short to count at all
    assert play_threshold(12) is None


async def test_long_track_needs_half_its_length(monkeypatch):
    a, reported = _app(monkeypatch)
    a.queue = Queue([Track(id="1", title="Long", duration="0:06:00")])

    await _listen(a, 179)
    assert reported == []                   # 30s rule would have counted long ago
    await _listen(a, 1)
    assert reported == [("Long", False)]


async def test_a_short_interlude_is_neither_a_play_nor_a_skip(monkeypatch):
    a, reported = _app(monkeypatch)
    a.queue = Queue([Track(id="1", title="Intro", duration="0:00:20"),
                     Track(id="2", title="Song", duration="0:03:00")])

    await _listen(a, 20)
    a.queue.advance()
    a._tick_play_time()
    await asyncio.sleep(0)
    assert reported == []
