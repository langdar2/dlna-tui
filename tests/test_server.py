import types
from dlna.server import MusicServer

DIDL = """<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
  <item id="i1" parentID="0"><dc:title>Song A</dc:title>
    <upnp:class>object.item.audioItem.musicTrack</upnp:class>
    <res protocolInfo="http-get:*:audio/mpeg:*">http://host/i1.mp3</res></item>
</DIDL-Lite>"""


class FakeProfile:
    async def async_browse_direct_children(self, object_id, **kw):
        return types.SimpleNamespace(result=DIDL, number_returned=1,
                                     total_matches=1, update_id=0)

    async def async_search_directory(self, container_id, search_criteria, **kw):
        return types.SimpleNamespace(result=DIDL, number_returned=1,
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
