# src/server_studio/installers/registry.py
from __future__ import annotations

from server_studio.installers.base import Installer
from server_studio.installers.vanilla import VanillaInstaller
from server_studio.installers.paper import PaperInstaller
from server_studio.installers.purpur import PurpurInstaller
from server_studio.installers.fabric import FabricInstaller

_BUILDERS = {
    "vanilla": VanillaInstaller,
    "paper": PaperInstaller,
    "purpur": PurpurInstaller,
    "fabric": FabricInstaller,
}

SUPPORTED_LOADERS = tuple(_BUILDERS)


def build_installer(loader: str, client) -> Installer:
    """Construct the installer for `loader`, sharing the given HTTP client."""
    try:
        builder = _BUILDERS[loader.lower()]
    except KeyError:
        raise ValueError(
            f"Unsupported loader: {loader!r}. Supported: {', '.join(SUPPORTED_LOADERS)}"
        )
    return builder(client=client)
