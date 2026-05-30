# src/server_studio/installers/runner.py
from __future__ import annotations

import subprocess
from pathlib import Path


def run_process(command: list[str], cwd: Path) -> None:
    """Run a command to completion in `cwd`; raise RuntimeError on non-zero exit."""
    result = subprocess.run(
        [str(c) for c in command],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        tail = (result.stdout or "")[-500:] + (result.stderr or "")[-500:]
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): {' '.join(map(str, command))}\n{tail}"
        )
