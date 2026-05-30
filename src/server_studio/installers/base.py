# src/server_studio/installers/base.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class InstallResult:
    jar_path: Path
    java_major: int


@runtime_checkable
class Installer(Protocol):
    """A loader installer: download the runnable server jar to `dest`."""

    def install(self, mc_version: str, dest: Path) -> InstallResult: ...
