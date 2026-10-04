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
