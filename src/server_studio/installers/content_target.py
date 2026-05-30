from __future__ import annotations

_MODS = {"fabric", "forge", "neoforge"}
_PLUGINS = {"paper", "purpur", "spigot"}


def content_dir_name(loader: str) -> str | None:
    key = loader.lower()
    if key in _MODS:
        return "mods"
    if key in _PLUGINS:
        return "plugins"
    return None


def supports_content(loader: str) -> bool:
    return content_dir_name(loader) is not None
