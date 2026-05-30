# src/server_studio/installers/neoforge.py
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from server_studio.installers.base import InstallResult
from server_studio.installers.launch_detect import detect_launch_args
from server_studio.java_versions import java_major_for_version

METADATA = "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml"
MAVEN = "https://maven.neoforged.net/releases/net/neoforged/neoforge"


def _build_number(version: str) -> int:
    """Trailing build number of a NeoForge version, ignoring any -beta/-rc suffix."""
    last = version.rsplit(".", 1)[-1]    # "236" or "0-beta"
    head = last.split("-", 1)[0]          # "236" or "0"
    return int(head) if head.isdigit() else -1


def neoforge_prefix(mc_version: str) -> str:
    """MC 1.X.Y -> NeoForge version prefix 'X.Y' (patch defaults to 0)."""
    parts = mc_version.split(".")
    minor = parts[1]
    patch = parts[2] if len(parts) > 2 else "0"
    return f"{minor}.{patch}"


class NeoForgeInstaller:
    """Installs a NeoForge server by running the official installer jar."""

    def __init__(self, client, java_resolver, runner):
        self._client = client
        self._java_resolver = java_resolver
        self._runner = runner

    def _neoforge_version(self, mc_version: str) -> str:
        resp = self._client.get(METADATA)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        versions = [e.text for e in root.iter("version") if e.text]
        prefix = neoforge_prefix(mc_version) + "."
        matching = [v for v in versions if v.startswith(prefix)]
        if not matching:
            raise ValueError(f"No NeoForge build for Minecraft {mc_version}")
        stable = [v for v in matching if "-" not in v.rsplit(".", 1)[-1]]
        return max(stable or matching, key=_build_number)

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        version = self._neoforge_version(mc_version)
        server_dir = dest.parent
        server_dir.mkdir(parents=True, exist_ok=True)

        installer_url = f"{MAVEN}/{version}/neoforge-{version}-installer.jar"
        resp = self._client.get(installer_url)
        resp.raise_for_status()
        installer_jar = server_dir / "neoforge-installer.jar"
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
