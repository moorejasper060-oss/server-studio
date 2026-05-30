# src/server_studio/installers/fabric.py
from __future__ import annotations

from pathlib import Path

from server_studio.installers.base import InstallResult
from server_studio.java_versions import java_major_for_version

META = "https://meta.fabricmc.net/v2/versions"


class FabricInstaller:
    """Resolves a Fabric server launcher jar via the Fabric Meta v2 API."""

    def __init__(self, client):
        self._client = client

    def _latest_stable_loader(self, game: str) -> str:
        resp = self._client.get(f"{META}/loader/{game}")
        resp.raise_for_status()
        entries = resp.json()
        for entry in entries:
            loader = entry.get("loader", {})
            if loader.get("stable"):
                return loader["version"]
        if entries:
            return entries[0]["loader"]["version"]
        raise ValueError(f"No Fabric loader for Minecraft {game}")

    def _latest_stable_installer(self) -> str:
        resp = self._client.get(f"{META}/installer")
        resp.raise_for_status()
        entries = resp.json()
        for entry in entries:
            if entry.get("stable"):
                return entry["version"]
        if entries:
            return entries[0]["version"]
        raise ValueError("No Fabric installer available")

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        loader = self._latest_stable_loader(mc_version)
        installer = self._latest_stable_installer()
        jar_url = f"{META}/loader/{mc_version}/{loader}/{installer}/server/jar"
        jar = self._client.get(jar_url)
        jar.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(jar.content)
        return InstallResult(jar_path=dest, java_major=java_major_for_version(mc_version))
