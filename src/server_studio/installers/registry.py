# src/server_studio/installers/registry.py
from __future__ import annotations

from server_studio.installers.base import Installer
from server_studio.installers.vanilla import VanillaInstaller
from server_studio.installers.paper import PaperInstaller
from server_studio.installers.purpur import PurpurInstaller
from server_studio.installers.fabric import FabricInstaller
from server_studio.installers.forge import ForgeInstaller
from server_studio.installers.neoforge import NeoForgeInstaller
from server_studio.installers.spigot import SpigotInstaller

_SIMPLE = {
    "vanilla": VanillaInstaller,
    "paper": PaperInstaller,
    "purpur": PurpurInstaller,
    "fabric": FabricInstaller,
}
_PROCESS = {
    "forge": ForgeInstaller,
    "neoforge": NeoForgeInstaller,
    "spigot": SpigotInstaller,
}

SUPPORTED_LOADERS = tuple(_SIMPLE) + tuple(_PROCESS)


def build_installer(loader: str, client, java_resolver=None, runner=None) -> Installer:
    """Construct the installer for `loader`, sharing the given HTTP client.

    Process-based loaders (forge/neoforge/spigot) also require `java_resolver` and
    `runner` because they run a Java process to install.
    """
    key = loader.lower()
    if key in _SIMPLE:
        return _SIMPLE[key](client=client)
    if key in _PROCESS:
        if java_resolver is None or runner is None:
            raise ValueError(f"Loader {loader!r} requires java_resolver and runner")
        return _PROCESS[key](client=client, java_resolver=java_resolver, runner=runner)
    raise ValueError(
        f"Unsupported loader: {loader!r}. Supported: {', '.join(SUPPORTED_LOADERS)}"
    )
