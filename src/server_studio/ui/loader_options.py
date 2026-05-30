# src/server_studio/ui/loader_options.py
from __future__ import annotations

from dataclasses import dataclass

from server_studio.installers.registry import SUPPORTED_LOADERS

_META = {
    "vanilla": ("Vanilla", "none", "Pure Minecraft, no mods or plugins."),
    "paper": ("Paper", "plugins", "Fast, optimized. Best for plugin servers."),
    "purpur": ("Purpur", "plugins", "Paper plus extra customization options."),
    "fabric": ("Fabric", "mods", "Lightweight modding. Great for performance mods."),
    "forge": ("Forge", "mods", "The classic big-modpack platform."),
    "neoforge": ("NeoForge", "mods", "Modern Forge fork, growing fast."),
    "spigot": ("Spigot", "plugins", "Bukkit-based plugins (compiled via BuildTools)."),
}


@dataclass(frozen=True)
class LoaderOption:
    key: str
    label: str
    kind: str        # "mods" | "plugins" | "none"
    description: str


def loader_options_for_version(mc_version: str) -> list[LoaderOption]:
    """Loaders valid for a version (currently all core-supported loaders)."""
    options = []
    for key in SUPPORTED_LOADERS:
        label, kind, desc = _META.get(key, (key.title(), "mods", ""))
        options.append(LoaderOption(key=key, label=label, kind=kind, description=desc))
    return options
