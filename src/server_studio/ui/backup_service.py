# src/server_studio/ui/backup_service.py
from __future__ import annotations


class BackupService:
    """Binds a BackupManager to one server for the BackupsTab interface."""

    def __init__(self, server_id: str, backup_manager):
        self._sid = server_id
        self._bm = backup_manager

    def create(self) -> str:
        return self._bm.create_backup(self._sid)

    def list(self) -> list[str]:
        return self._bm.list_backups(self._sid)

    def restore(self, name: str) -> None:
        self._bm.restore_backup(self._sid, name)

    def delete(self, name: str) -> None:
        self._bm.delete_backup(self._sid, name)
