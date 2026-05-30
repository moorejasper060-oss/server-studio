# src/server_studio/installers/purpur.py
from __future__ import annotations

from pathlib import Path

from server_studio.installers.base import InstallResult
from server_studio.java_versions import java_major_for_version

BASE = "https://api.purpurmc.org/v2/purpur"


class PurpurInstaller:
    """Resolves the latest Purpur build for a version via the PurpurMC v2 API."""

    def __init__(self, client):
        self._client = client

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        meta = self._client.get(f"{BASE}/{mc_version}")
        meta.raise_for_status()
        latest = meta.json().get("builds", {}).get("latest")
        if not latest:
            raise ValueError(f"No Purpur builds for Minecraft {mc_version}")

        jar = self._client.get(f"{BASE}/{mc_version}/{latest}/download")
        jar.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(jar.content)
        return InstallResult(jar_path=dest, java_major=java_major_for_version(mc_version))
