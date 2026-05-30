# src/server_studio/java_manager.py
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from server_studio.paths import AppPaths


def _java_exe_name() -> str:
    return "java.exe" if sys.platform == "win32" else "java"


class JavaManager:
    """Resolves a cached Java executable, downloading Temurin on demand.

    `fetcher(major: int, dest_dir: Path)` must populate `dest_dir` with a Temurin
    runtime (so that `dest_dir / "bin" / java[.exe]` exists). It is injected so the
    network download + archive extraction can be tested separately and so this class
    stays offline-testable.
    """

    def __init__(self, paths: AppPaths, fetcher: Callable[[int, Path], None]):
        self._paths = paths
        self._fetcher = fetcher

    def _runtime_dir(self, major: int) -> Path:
        return self._paths.java / f"temurin-{major}"

    def _exe_path(self, major: int) -> Path:
        return self._runtime_dir(major) / "bin" / _java_exe_name()

    def resolve(self, major: int) -> Path:
        exe = self._exe_path(major)
        if exe.is_file():
            return exe

        dest_dir = self._runtime_dir(major)
        dest_dir.mkdir(parents=True, exist_ok=True)
        self._fetcher(major, dest_dir)

        if not exe.is_file():
            raise RuntimeError(
                f"Java {major} download did not produce an executable at {exe}"
            )
        return exe

    @property
    def resolver(self) -> Callable[[int], Path]:
        return self.resolve
