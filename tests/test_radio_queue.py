from dlna.models import Queue, Track
from ui import app as app_mod
from ui.app import DlnaApp


def _app(tracks):
    a = DlnaApp(store=None, requester=None, event_handler=None)
    a.queue = Queue(list(tracks))
    return a


async def test_radio_results_dropped_when_user_picks_another_track(monkeypatch):
    """A radio fetch takes a second or two. If the user picks a new song while
    it runs, its suggestions must not land in that song's queue."""
    a = _app([Track(id="a", title="A")])

    async def fetch(*args, **kwargs):
        a._queue_gen += 1  # user picked a different track mid-fetch
        return [Track(id="r", title="Radio pick")]

    monkeypatch.setattr(app_mod, "radio_tracks", fetch)
    assert await a._append_radio(Track(id="a", title="A")) is None
    assert [t.id for t in a.queue.tracks] == ["a"]  # nothing appended


async def test_radio_results_kept_when_queue_untouched(monkeypatch):
    a = _app([Track(id="a", title="A")])
    monkeypatch.setattr(app_mod, "radio_tracks",
                        lambda *args, **kwargs: _recs())
    # _append_radio redraws the queue pane once it adds something, which needs a
    # mounted app; stub it out so this stays a plain logic check.
    monkeypatch.setattr(DlnaApp, "_sync_queue_view", _noop)
    assert await a._append_radio(Track(id="a", title="A")) == 1
    assert [t.id for t in a.queue.tracks] == ["a", "r"]


async def _recs():
    return [Track(id="r", title="Radio pick", artist="X")]


async def _noop(self):
    pass


async def test_handoff_stops_the_app_advancing(monkeypatch):
    """Once VuIO drives the playlist, this app must not also push tracks at the
    renderer -- two schedulers on one device fight over it."""
    played = []

    class FakeRenderer:
        def state(self):
            from dlna.renderer import RendererState
            return RendererState(transport_state="STOPPED")

        async def update(self):
            return True

        async def play(self, track):
            played.append(track.id)
            return True

    class Info:
        udn = "uuid:test"
        name = "Evo One"
        location = "http://10.0.0.5:8050/d.xml"

    async def fake_handoff(tracks, udn, location="", index=0, name=""):
        assert (udn, location) == ("uuid:test", "http://10.0.0.5:8050/d.xml")
        return len(tracks), "chromecast"

    monkeypatch.setattr(app_mod, "handoff", fake_handoff)

    class T(DlnaApp):
        async def on_mount(self):
            pass

    a = T(store=None, requester=None, event_handler=None)
    async with a.run_test() as pilot:
        a.queue = Queue([Track(id="1", title="A"), Track(id="2", title="B")])
        a.renderer = FakeRenderer()
        a._rnd_info = Info()

        a._last_state = "PLAYING"      # app still in charge: the edge advances
        a._refresh_state()
        await pilot.pause()            # _refresh_state spawns play() as a task
        assert played == ["2"]

        await a.action_handoff()
        assert a.handed_off is True
        assert a.radio is False

        played.clear()
        a.queue.index = 0
        a._last_state = "PLAYING"      # same edge, now VuIO's job
        a._refresh_state()
        await pilot.pause()
        assert played == []
