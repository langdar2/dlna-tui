"""Regressions from review of the display/cover-cache/radio-guard changes."""
import warnings

from dlna.models import Queue, Track
from dlna.renderer import RendererState
from ui import app as app_mod
from ui.app import DlnaApp


class _Renderer:
    def __init__(self):
        self.played = []

    def state(self):
        return RendererState(transport_state="PLAYING", position=10)

    async def update(self):
        return True

    async def play(self, track):
        self.played.append(track.id)
        return True


class _App(DlnaApp):
    async def on_mount(self):
        pass


async def _noop(self):
    pass


async def test_poll_survives_a_track_with_a_duration_and_no_pixel_display():
    """Textual's own App.display is True, so the pixel display must not be
    reached through that name; and Track.duration is a string."""
    a = _App(store=None, requester=None, event_handler=None)
    async with a.run_test():
        a.renderer = _Renderer()
        a.queue = Queue([Track(id="1", title="A", duration="0:03:00")])
        await a._poll()  # must not raise


async def test_auto_radio_fetches_when_the_queue_runs_dry(monkeypatch):
    fetched = []

    async def fake_radio(*args, **kwargs):
        fetched.append(1)
        return [Track(id="r", title="R", artist="X")]

    monkeypatch.setattr(app_mod, "radio_tracks", fake_radio)
    monkeypatch.setattr(DlnaApp, "_sync_queue_view", _noop)
    a = DlnaApp(store=None, requester=None, event_handler=None)
    a.queue = Queue([Track(id="1", title="A")])
    a.renderer = _Renderer()

    await a._radio_continue()

    assert fetched == [1]
    assert a.renderer.played == ["r"]
    assert a._radio_busy is False


async def test_a_failed_radio_fetch_does_not_leave_radio_stuck_busy(monkeypatch):
    async def broken(*args, **kwargs):
        raise RuntimeError("CrateMind down")

    monkeypatch.setattr(app_mod, "radio_tracks", broken)
    a = DlnaApp(store=None, requester=None, event_handler=None)
    a.queue = Queue([Track(id="1", title="A")])
    a.renderer = _Renderer()
    try:
        await a._radio_continue()
    except RuntimeError:
        pass
    assert a._radio_busy is False


async def test_radio_seeds_from_the_playing_track_when_no_track_is_selected():
    a = _App(store=None, requester=None, event_handler=None)
    async with a.run_test():
        a.queue = Queue([Track(id="1", title="Playing")])
        assert a._seed_track().id == "1"


async def test_escape_in_the_filter_clears_it_and_restores_the_tree(monkeypatch):
    restored = []

    async def fake_fill(self, node, cid, q=None):
        restored.append(q)

    monkeypatch.setattr(DlnaApp, "_fill", fake_fill)
    a = _App(store=None, requester=None, event_handler=None)
    async with a.run_test() as pilot:
        a.server = object()               # filtering only runs with a server
        a._filter_node = a.query_one("#browser").root
        box = a.query_one("#filter")
        box.focus()
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)  # unawaited coroutine
            await pilot.press("escape")
            await pilot.pause()
        assert box.value == ""
        assert a._filter_node is None
        assert None in restored            # folder refilled without a query


def _subtitle(radio, busy, n):
    a = DlnaApp(store=None, requester=None, event_handler=None)
    a.radio, a._radio_busy = radio, busy
    a.queue = Queue([Track(id=str(i), title="t") for i in range(n)])
    a._update_subtitle()
    return a.sub_title


def test_subtitle_shows_the_radio_icon_only_while_radio_is_on():
    assert "📻" not in _subtitle(False, False, 31)
    assert "31 Titel" in _subtitle(False, False, 31)
    assert "📻 Radio (12)" in _subtitle(True, False, 12)
    assert "⏳" in _subtitle(True, True, 12)
    assert "Titel" not in _subtitle(False, False, 0)


async def test_cover_is_cached_and_a_failure_says_why(tmp_path, monkeypatch):
    monkeypatch.setattr(app_mod, "_COVER_CACHE", tmp_path / "covers")
    fetches = []

    def fake_get(url):
        fetches.append(url)
        if "broken" in url:
            raise OSError("404")
        return b"img"

    monkeypatch.setattr(app_mod, "_http_get", fake_get)
    monkeypatch.setattr(app_mod, "to_ansi", lambda data, width: f"art{width}")

    assert await app_mod._get_cover_data("http://h/a.jpg", 40) == "art40"
    assert await app_mod._get_cover_data("http://h/a.jpg", 60) == "art60"  # width follows the box
    assert fetches == ["http://h/a.jpg"]                                  # second hit from cache

    msg = await app_mod._get_cover_data("http://h/broken.jpg", 40)
    assert "404" in msg


def test_importing_the_app_does_not_create_the_cover_cache():
    import importlib, inspect
    src = inspect.getsource(importlib.import_module("ui.app"))
    module_level = [l for l in src.splitlines() if l.startswith("_COVER_CACHE.mkdir")]
    assert module_level == []
