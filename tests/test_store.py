import json

from dlna.store import Store


def test_roundtrip(tmp_path):
    path = tmp_path / "store.json"
    s = Store(path)
    s.set_rating("i1", 1, "Song A")
    s.last_server = "uuid-server"
    s.last_renderer = "uuid-renderer"
    s.save()

    s2 = Store(path)
    assert s2.rating_of("i1") == 1
    assert s2.last_server == "uuid-server"
    assert s2.last_renderer == "uuid-renderer"


def test_rating_toggles_off_and_is_persisted(tmp_path):
    path = tmp_path / "store.json"
    s = Store(path)
    s.set_rating("i1", 1, "Song A")
    s.set_rating("i2", -1, "Song B")
    s.set_rating("i1", 0)

    s2 = Store(path)
    assert s2.rating_of("i1") == 0  # cleared
    assert s2.rating_of("i2") == -1
    assert s2.rating_of("never-rated") == 0


def test_old_favourites_file_becomes_ratings(tmp_path):
    """Stores written before ratings existed must not lose their favourites."""
    path = tmp_path / "store.json"
    path.write_text(json.dumps({
        "favorites": [{"id": "i1", "title": "Song A", "media_url": "http://h/1"}],
        "last_server": "uuid-server",
    }))

    s = Store(path)
    assert s.rating_of("i1") == 1
    assert s.last_server == "uuid-server"


def test_corrupt_file_is_ignored(tmp_path):
    path = tmp_path / "store.json"
    path.write_text("{ not json")
    s = Store(path)  # must not crash
    assert s.ratings == {}
    assert s.last_server is None


def test_missing_file(tmp_path):
    s = Store(tmp_path / "nope.json")
    assert s.ratings == {}
