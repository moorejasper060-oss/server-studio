# src/server_studio/ui/settings_store.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from server_studio.paths import AppPaths
from server_studio.ui.theme import THEMES, DEFAULT_THEME

_FILENAME = "settings.json"


@dataclass
class AppSettings:
    theme: str = DEFAULT_THEME

    @staticmethod
    def _path(paths: AppPaths) -> Path:
        return paths.root / _FILENAME

    @classmethod
    def load(cls, paths: AppPaths) -> "AppSettings":
        path = cls._path(paths)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            theme = data.get("theme", DEFAULT_THEME)
        except (FileNotFoundError, ValueError):
            theme = DEFAULT_THEME
        if theme not in THEMES:
            theme = DEFAULT_THEME
        return cls(theme=theme)

    def save(self, paths: AppPaths) -> None:
        self._path(paths).write_text(
            json.dumps({"theme": self.theme}, indent=2), encoding="utf-8"
        )
