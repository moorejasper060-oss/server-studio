# src/server_studio/installers/spigot.py
from __future__ import annotations

from pathlib import Path

from server_studio.installers.base import InstallResult
from server_studio.java_versions import java_major_for_version

BUILDTOOLS = (
    "https://hub.spigotmc.org/jenkins/job/BuildTools/"
    "lastSuccessfulBuild/artifact/target/BuildTools.jar"
)


class SpigotInstaller:
    """Builds a Spigot server jar via BuildTools."""

    def __init__(self, client, java_resolver, runner):
        self._client = client
        self._java_resolver = java_resolver
        self._runner = runner

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        server_dir = dest.parent
        work = server_dir / "buildtools"
        work.mkdir(parents=True, exist_ok=True)

        resp = self._client.get(BUILDTOOLS)
        resp.raise_for_status()
        (work / "BuildTools.jar").write_bytes(resp.content)

        java_major = java_major_for_version(mc_version)
        java = self._java_resolver(java_major)
        self._runner(
            [str(java), "-jar", "BuildTools.jar", "--rev", mc_version],
            work,
        )

        built = work / f"spigot-{mc_version}.jar"
        if not built.is_file():
            matches = sorted(work.glob("spigot-*.jar"))
            if not matches:
                raise RuntimeError("BuildTools did not produce a Spigot jar")
            built = matches[0]

        dest.write_bytes(built.read_bytes())
        return InstallResult(jar_path=dest, java_major=java_major)
