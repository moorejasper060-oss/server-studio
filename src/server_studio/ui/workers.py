# src/server_studio/ui/workers.py
from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class CreateServerWorker(QObject):
    """Creates a server (jar + Java download) off the UI thread.

    Move an instance to a QThread and call run() on thread start; it emits exactly one
    of finished/failed.
    """

    finished = Signal(object)   # ServerConfig
    failed = Signal(str)

    def __init__(self, manager, *, name: str, mc_version: str, loader: str, ram_mb: int):
        super().__init__()
        self._manager = manager
        self._args = dict(name=name, mc_version=mc_version, loader=loader, ram_mb=ram_mb)

    def run(self) -> None:
        try:
            cfg = self._manager.create_server(**self._args)
        except Exception as exc:  # surfaced to the user as a friendly message
            self.failed.emit(str(exc))
            return
        self.finished.emit(cfg)
