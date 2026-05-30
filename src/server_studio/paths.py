from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    """Owns the on-disk layout for Server Studio data."""

    root: Path

    @property
    def servers(self) -> Path:
        return self.root / "servers"

    @property
    def java(self) -> Path:
        return self.root / "java"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    def server_dir(self, server_id: str) -> Path:
        return self.servers / server_id

    def ensure(self) -> None:
        for path in (self.servers, self.java, self.cache, self.backups):
            path.mkdir(parents=True, exist_ok=True)
