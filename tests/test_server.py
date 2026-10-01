import types
from didl_lite import didl_lite
from dlna.server import MusicServer

DIDL = """<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
  <item id="i1" parentID="0"><dc:title>Song A</dc:title>
    <upnp:class>object.item.audioItem.musicTrack</upnp:class>
    <res protocolInfo="http-get:*:audio/mpeg:*">http://host/i1.mp3</res></item>
</DIDL-Lite>"""

# Real BrowseResult.result is an already-parsed list of didl_lite objects, not XML.
PARSED = didl_lite.from_xml_string(DIDL, strict=False)


class FakeProfile:
    async def async_browse_direct_children(self, object_id, **kw):
        return types.SimpleNamespace(result=PARSED, number_returned=1,
                                     total_matches=1, update_id=0)

    async def async_search_directory(self, container_id, search_criteria, **kw):
        return types.SimpleNamespace(result=PARSED, number_returned=1,
                                     total_matches=1, update_id=0)


async def test_browse_returns_models():
    srv = MusicServer(FakeProfile())
    items = await srv.browse("0")
    assert len(items) == 1
    assert items[0].title == "Song A"
    assert items[0].media_url == "http://host/i1.mp3"


async def test_search_returns_models():
    srv = MusicServer(FakeProfile())
    items = await srv.search("rock")
    assert items[0].title == "Song A"


# Server without a Search action: fallback must recurse into subcontainers.
ROOT = didl_lite.from_xml_string("""<DIDL-Lite
  xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
  <container id="album1" parentID="0"><dc:title>Album</dc:title>
    <upnp:class>object.container.album.musicAlbum</upnp:class></container>
</DIDL-Lite>""", strict=False)

ALBUM = didl_lite.from_xml_string("""<DIDL-Lite
  xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
  <item id="t1" parentID="album1"><dc:title>Hello World</dc:title>
    <upnp:class>object.item.audioItem.musicTrack</upnp:class>
    <res protocolInfo="http-get:*:audio/mpeg:*">http://host/t1.mp3</res></item>
</DIDL-Lite>""", strict=False)


class NoSearchProfile:
    async def async_browse_direct_children(self, object_id, **kw):
        objs = ROOT if object_id == "0" else ALBUM
        return types.SimpleNamespace(result=objs)

    async def async_search_directory(self, *a, **kw):
        raise RuntimeError("Missing action CD/Search")


async def test_search_recurses_when_no_search_action():
    srv = MusicServer(NoSearchProfile())
    items = await srv.search("hello")
    assert len(items) == 1 and items[0].title == "Hello World"
    assert await srv.search("nomatch") == []
