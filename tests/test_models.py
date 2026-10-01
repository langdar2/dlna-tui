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
