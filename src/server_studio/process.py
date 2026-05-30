from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Callable


class ServerProcess:
    """Runs and supervises a server subprocess, streaming stdout to a callback.

    `on_output` is called once per output line (newline stripped) from a reader
    thread — consumers must be thread-safe or marshal to their UI thread.
    """

    def __init__(self, command: list[str], cwd: Path, on_output: Callable[[str], None]):
        self._command = command
        self._cwd = cwd
        self._on_output = on_output
        self._proc: subprocess.Popen | None = None
        self._reader: threading.Thread | None = None

    def start(self) -> None:
        if self.is_running():
            raise RuntimeError("Process already running")
        self._proc = subprocess.Popen(
            self._command,
            cwd=str(self._cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._reader = threading.Thread(target=self._pump_output, daemon=True)
        self._reader.start()

    def _pump_output(self) -> None:
        assert self._proc and self._proc.stdout
        for line in self._proc.stdout:
            self._on_output(line.rstrip("\n"))

    def send(self, command: str) -> None:
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("Process not running")
        self._proc.stdin.write(command + "\n")
        self._proc.stdin.flush()

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def stop(self, timeout: float = 10.0) -> None:
        if not self._proc:
            return
        # Graceful: Minecraft servers stop on the "stop" command via stdin.
        try:
            if self._proc.stdin and not self._proc.stdin.closed:
                self._proc.stdin.write("stop\n")
                self._proc.stdin.flush()
        except (OSError, ValueError):
            pass
        try:
            self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._proc.kill()
