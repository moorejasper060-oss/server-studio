from __future__ import annotations

import re
from pathlib import Path
from typing import Callable


class BoreTunnel:
    """Exposes a local port over the internet via the `bore` TCP tunnel.

    `process_factory(command, cwd, on_output)` returns a process with start()/stop()/
    is_running() — the same shape as ServerProcess, so it's injectable for tests.
    """

    def __init__(self, port: int, cwd: Path, process_factory: Callable,
                 bore_path: str = "bore", remote_host: str = "bore.pub",
                 on_address: Callable[[str], None] | None = None):
        self._port = port
        self._cwd = cwd
        self._factory = process_factory
        self._bore_path = bore_path
        self._remote_host = remote_host
        self._on_address = on_address
        self._proc = None
        self._address: str | None = None
        self._re = re.compile(rf"({re.escape(remote_host)}:\d+)")

    def start(self) -> None:
        command = [self._bore_path, "local", str(self._port), "--to", self._remote_host]
        self._proc = self._factory(command, self._cwd, self._on_output)
        self._proc.start()

    def _on_output(self, line: str) -> None:
        if self._address:
            return
        match = self._re.search(line)
        if match:
            self._address = match.group(1)
            if self._on_address:
                self._on_address(self._address)

    @property
    def address(self) -> str | None:
        return self._address

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.is_running()

    def stop(self) -> None:
        if self._proc:
            self._proc.stop()
            self._proc = None
        self._address = None
