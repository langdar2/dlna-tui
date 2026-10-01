from __future__ import annotations

import json
from pathlib import Path


def default_path() -> Path:
    return Path.home() / ".config" / "dlna-tui" / "store.json"


class Store:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else default_path()
        self.favorites: list[dict] = []
        self.last_server: str | None = None
        self.last_renderer: str | None = None
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return  # missing or corrupt -> defaults
        self.favorites = data.get("favorites", [])
        self.last_server = data.get("last_server")
        self.last_renderer = data.get("last_renderer")

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({
            "favorites": self.favorites,
            "last_server": self.last_server,
            "last_renderer": self.last_renderer,
        }, indent=2))
