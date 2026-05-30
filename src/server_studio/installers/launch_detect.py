# src/server_studio/installers/launch_detect.py
from __future__ import annotations

from pathlib import Path


def detect_launch_args(server_dir: Path) -> list[str]:
    """Determine how a Forge/NeoForge install should be launched.

    Modern installers (MC 1.17+) produce libraries/.../win_args.txt; older ones produce
    a runnable forge-<ver>.jar. Falls back to the plain server.jar form.
    """
    args_files = sorted(server_dir.glob("libraries/**/win_args.txt"))
    if args_files:
        rel = args_files[0].relative_to(server_dir).as_posix()
        return [f"@{rel}", "nogui"]

    for pattern in ("forge-*.jar", "neoforge-*.jar"):
        for jar in sorted(server_dir.glob(pattern)):
            if "installer" not in jar.name:
                return ["-jar", jar.name, "nogui"]

    return ["-jar", "server.jar", "nogui"]
