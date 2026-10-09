from __future__ import annotations

import json
from pathlib import Path


def default_path() -> Path:
    return Path.home() / ".config" / "dlna-tui" / "store.json"


class Store:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else default_path()
        # track id -> {"rating": +1|-1, "title": str}. CrateMind holds the
        # authoritative copy, but it only knows tracks it has analysed, and the
        # player must still show a rating while it is unreachable.
        self.ratings: dict[str, dict] = {}
        self.last_server: str | None = None
        self.last_renderer: str | None = None
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return  # missing or corrupt -> defaults
        self.ratings = data.get("ratings", {})
        for fav in data.get("favorites", []):  # pre-ratings store
            self.ratings.setdefault(str(fav.get("id")),
                                    {"rating": 1, "title": fav.get("title", "")})
        self.last_server = data.get("last_server")
        self.last_renderer = data.get("last_renderer")

    def rating_of(self, track_id: str) -> int:
        entry = self.ratings.get(str(track_id))
        return entry["rating"] if entry else 0

    def set_rating(self, track_id: str, rating: int, title: str = "") -> None:
        if rating:
            self.ratings[str(track_id)] = {"rating": rating, "title": title}
        else:
            self.ratings.pop(str(track_id), None)
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({
            "ratings": self.ratings,
            "last_server": self.last_server,
            "last_renderer": self.last_renderer,
        }, indent=2))
