import types
from dlna.renderer import Renderer, RendererState


class FakeProfile:
    def __init__(self):
        self.transport_state = "PLAYING"
        self.media_position = 42
        self.media_duration = 200
        self.volume_level = 0.5
        self.media_title = "Song A"
        self.played = None

    async def async_set_transport_uri(self, media_url, media_title, meta_data=None):
        self.played = media_url

    async def async_play(self):
        pass

    async def async_stop(self):
        raise RuntimeError("device gone")


async def test_state_snapshot():
    r = Renderer(FakeProfile())
    st = r.state()
    assert isinstance(st, RendererState)
    assert st.transport_state == "PLAYING"
    assert st.position == 42
    assert st.duration == 200
    assert st.volume == 0.5
    assert st.title == "Song A"


async def test_safe_call_swallows_errors_and_reports():
    errors = []
    r = Renderer(FakeProfile(), on_error=errors.append)
    ok = await r.stop()  # profile raises -> must not propagate
    assert ok is False
    assert errors and "device gone" in errors[0]


async def test_play_sets_uri(tmp_path):
    from dlna.models import Track
    prof = FakeProfile()
    r = Renderer(prof)
    ok = await r.play(Track(id="i1", title="Song A", media_url="http://h/x.mp3"))
    assert ok is True
    assert prof.played == "http://h/x.mp3"
