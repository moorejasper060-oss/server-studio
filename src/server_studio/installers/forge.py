# src/server_studio/installers/forge.py
from __future__ import annotations

from pathlib import Path

from server_studio.installers.base import InstallResult
from server_studio.installers.launch_detect import detect_launch_args
from server_studio.java_versions import java_major_for_version

PROMOTIONS = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
MAVEN = "https://maven.minecraftforge.net/net/minecraftforge/forge"


class ForgeInstaller:
    """Installs a Forge server by running the official installer jar."""

    def __init__(self, client, java_resolver, runner):
        self._client = client
        self._java_resolver = java_resolver
        self._runner = runner

    def _forge_version(self, mc_version: str) -> str:
        resp = self._client.get(PROMOTIONS)
        resp.raise_for_status()
        promos = resp.json().get("promos", {})
        version = promos.get(f"{mc_version}-recommended") or promos.get(f"{mc_version}-latest")
        if not version:
            raise ValueError(f"No Forge build for Minecraft {mc_version}")
        return version

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        forge_version = self._forge_version(mc_version)
        full = f"{mc_version}-{forge_version}"
        server_dir = dest.parent
        server_dir.mkdir(parents=True, exist_ok=True)

        installer_url = f"{MAVEN}/{full}/forge-{full}-installer.jar"
        resp = self._client.get(installer_url)
        resp.raise_for_status()
        installer_jar = server_dir / "forge-installer.jar"
        installer_jar.write_bytes(resp.content)

        java_major = java_major_for_version(mc_version)
        java = self._java_resolver(java_major)
        self._runner(
            [str(java), "-jar", installer_jar.name, "--installServer"],
            server_dir,
        )

        return InstallResult(
            jar_path=server_dir / "server.jar",
            java_major=java_major,
            launch_args=detect_launch_args(server_dir),
        )
