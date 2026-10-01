from dlna.store import Store


def test_roundtrip(tmp_path):
    path = tmp_path / "store.json"
    s = Store(path)
    s.favorites.append({"id": "i1", "title": "Song A"})
    s.last_server = "uuid-server"
    s.last_renderer = "uuid-renderer"
    s.save()

    s2 = Store(path)
    assert s2.favorites == [{"id": "i1", "title": "Song A"}]
    assert s2.last_server == "uuid-server"
    assert s2.last_renderer == "uuid-renderer"


def test_corrupt_file_is_ignored(tmp_path):
    path = tmp_path / "store.json"
    path.write_text("{ not json")
    s = Store(path)  # must not crash
    assert s.favorites == []
    assert s.last_server is None


def test_missing_file(tmp_path):
    s = Store(tmp_path / "nope.json")
    assert s.favorites == []
