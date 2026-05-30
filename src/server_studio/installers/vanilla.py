# src/server_studio/installers/vanilla.py
from __future__ import annotations

from pathlib import Path

from server_studio.installers.base import InstallResult

MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"


class VanillaInstaller:
    """Resolves a Vanilla server jar via the Mojang version manifest.

    `client` must expose `.get(url)` returning an object with `.json()`,
    `.content`, and `.raise_for_status()` (httpx.Client is compatible).
    """

    def __init__(self, client):
        self._client = client

    def _version_url(self, mc_version: str) -> str:
        resp = self._client.get(MANIFEST_URL)
        resp.raise_for_status()
        for entry in resp.json().get("versions", []):
            if entry.get("id") == mc_version:
                return entry["url"]
        raise ValueError(f"Unknown Minecraft version: {mc_version}")

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        version_url = self._version_url(mc_version)
        meta = self._client.get(version_url)
        meta.raise_for_status()
        meta_json = meta.json()
        jar_url = meta_json["downloads"]["server"]["url"]
        java_major = int(meta_json.get("javaVersion", {}).get("majorVersion", 21))

        jar = self._client.get(jar_url)
        jar.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(jar.content)
        return InstallResult(jar_path=dest, java_major=java_major)
