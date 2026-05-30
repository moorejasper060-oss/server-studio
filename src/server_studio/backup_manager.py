from __future__ import annotations

import zipfile
from datetime import datetime
from typing import Callable

from server_studio.paths import AppPaths


class BackupManager:
    """Snapshots a server's world directories to timestamped zips."""

    def __init__(self, paths: AppPaths, clock: Callable[[], datetime] | None = None):
        self._paths = paths
        self._clock = clock or datetime.now

    def _dir(self, server_id: str):
        d = self._paths.backups / server_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def create_backup(self, server_id: str) -> str:
        sdir = self._paths.server_dir(server_id)
        base = self._clock().strftime("%Y%m%d-%H%M%S")
        d = self._dir(server_id)
        name = f"{base}.zip"
        n = 2
        while (d / name).exists():
            name = f"{base}-{n}.zip"
            n += 1
        worlds = [p for p in sorted(sdir.glob("world*")) if p.is_dir()]
        with zipfile.ZipFile(d / name, "w", zipfile.ZIP_DEFLATED) as zf:
            for world in worlds:
                for f in world.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(sdir).as_posix())
        return name

    def list_backups(self, server_id: str) -> list[str]:
        d = self._paths.backups / server_id
        if not d.is_dir():
            return []
        return sorted((p.name for p in d.glob("*.zip")), reverse=True)

    def restore_backup(self, server_id: str, name: str) -> None:
        archive = self._paths.backups / server_id / name
        if not archive.is_file():
            raise FileNotFoundError(f"No backup named {name}")
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(self._paths.server_dir(server_id))

    def delete_backup(self, server_id: str, name: str) -> None:
        archive = self._paths.backups / server_id / name
        if archive.is_file():
            archive.unlink()
