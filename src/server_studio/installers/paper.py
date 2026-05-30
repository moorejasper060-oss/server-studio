# src/server_studio/installers/paper.py
from __future__ import annotations

from pathlib import Path

from server_studio.installers.base import InstallResult
from server_studio.java_versions import java_major_for_version

BASE = "https://api.papermc.io/v2/projects/paper/versions"


class PaperInstaller:
    """Resolves the latest Paper build for a version via the PaperMC v2 API."""

    def __init__(self, client):
        self._client = client

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        builds_resp = self._client.get(f"{BASE}/{mc_version}")
        builds_resp.raise_for_status()
        builds = builds_resp.json().get("builds", [])
        if not builds:
            raise ValueError(f"No Paper builds for Minecraft {mc_version}")
        build = max(builds)

        build_resp = self._client.get(f"{BASE}/{mc_version}/builds/{build}")
        build_resp.raise_for_status()
        jar_name = build_resp.json()["downloads"]["application"]["name"]

        download_url = f"{BASE}/{mc_version}/builds/{build}/downloads/{jar_name}"
        jar = self._client.get(download_url)
        jar.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(jar.content)
        return InstallResult(jar_path=dest, java_major=java_major_for_version(mc_version))
