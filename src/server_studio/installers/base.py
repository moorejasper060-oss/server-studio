# src/server_studio/installers/base.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


def _default_launch_args() -> list[str]:
    return ["-jar", "server.jar", "nogui"]


@dataclass
class InstallResult:
    jar_path: Path
    java_major: int
    launch_args: list[str] = field(default_factory=_default_launch_args)


@runtime_checkable
class Installer(Protocol):
    """A loader installer: download/produce the runnable server in `dest`'s directory."""

    def install(self, mc_version: str, dest: Path) -> InstallResult: ...
