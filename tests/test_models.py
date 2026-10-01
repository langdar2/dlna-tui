from dlna.models import Track, Container, from_didl

DIDL = """<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
  <container id="c1" parentID="0" childCount="7"><dc:title>Album X</dc:title>
    <upnp:class>object.container.album.musicAlbum</upnp:class></container>
  <item id="i1" parentID="c1"><dc:title>Song A</dc:title>
    <upnp:artist>Artist A</upnp:artist><upnp:album>Album X</upnp:album>
    <upnp:class>object.item.audioItem.musicTrack</upnp:class>
    <res protocolInfo="http-get:*:audio/mpeg:*" duration="0:03:20.000">http://host/i1.mp3</res>
  </item>
</DIDL-Lite>"""

def test_from_didl_parses_container_and_track():
    objs = from_didl(DIDL)
    assert len(objs) == 2
    cont, track = objs
    assert isinstance(cont, Container)
    assert cont.id == "c1" and cont.title == "Album X" and cont.child_count == 7
    assert isinstance(track, Track)
    assert track.id == "i1"
    assert track.title == "Song A"
    assert track.artist == "Artist A"
    assert track.album == "Album X"
    assert track.media_url == "http://host/i1.mp3"
    assert track.duration == "0:03:20.000"
    assert "<item id=\"i1\"" in track.didl


DIDL_FLAC = """<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
  <item id="i2" parentID="c1"><dc:title>Song B</dc:title>
    <upnp:class>object.item.audioItem.musicTrack</upnp:class>
    <res protocolInfo="http-get:*:audio/flac:*" sampleFrequency="44100"
      bitsPerSample="16" nrAudioChannels="2" size="29360128"
      duration="0:03:20.000">http://host/i2.flac</res>
  </item>
</DIDL-Lite>"""


def test_media_info_summary():
    track = from_didl(DIDL_FLAC)[0]
    assert track.info == "flac · 44.1kHz · 16bit · 2ch · 28.0 MB"


DIDL_MIXED = """<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
  <item id="a" parentID="0"><dc:title>Audio</dc:title>
    <upnp:class>object.item.audioItem.musicTrack</upnp:class>
    <res protocolInfo="http-get:*:audio/mpeg:*">http://h/a.mp3</res></item>
  <item id="v" parentID="0"><dc:title>Movie</dc:title>
    <upnp:class>object.item.videoItem.movie</upnp:class>
    <res protocolInfo="http-get:*:video/mp4:*">http://h/v.mp4</res></item>
</DIDL-Lite>"""


def test_video_items_are_filtered_out():
    objs = from_didl(DIDL_MIXED)
    assert [o.title for o in objs] == ["Audio"]


from dlna.models import Queue


def _t(i):
    return Track(id=i, title=i)


def test_queue_advance_moves_forward():
    q = Queue([_t("a"), _t("b"), _t("c")])
    assert q.current().id == "a"
    assert q.advance().id == "b"
    assert q.advance().id == "c"
    assert q.advance() is None  # Ende


def test_queue_prev_and_append():
    q = Queue([_t("a")])
    q.append(_t("b"))
    q.advance()
    assert q.current().id == "b"
    assert q.prev().id == "a"


def test_empty_queue():
    q = Queue([])
    assert q.current() is None
    assert q.advance() is None
