# src/server_studio/java_versions.py
from __future__ import annotations

DEFAULT_JAVA_MAJOR = 21


def java_major_for_version(mc_version: str) -> int:
    """Map a Minecraft *release* version (e.g. "1.20.6") to the required Java major.

    Rules (Mojang's): <=1.16 → 8, 1.17–1.20.4 → 17, >=1.20.5 → 21.
    Unparseable or snapshot strings fall back to the latest (21).
    """
    parts = mc_version.split(".")
    try:
        if parts[0] != "1":
            return DEFAULT_JAVA_MAJOR
        minor = int(parts[1])
        patch = int(parts[2]) if len(parts) > 2 else 0
    except (IndexError, ValueError):
        return DEFAULT_JAVA_MAJOR

    if minor <= 16:
        return 8
    if minor <= 19:
        return 17
    if minor == 20:
        return 17 if patch < 5 else 21
    return 21
