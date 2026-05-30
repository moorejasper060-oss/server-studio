# src/server_studio/installers/version_list.py
from __future__ import annotations

MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
DEFAULT_VERSIONS = ["1.21.4", "1.20.6", "1.20.4", "1.16.5"]


def list_release_versions(client) -> list[str]:
    """Fetch Minecraft *release* version ids (newest first) from the Mojang manifest."""
    resp = client.get(MANIFEST_URL)
    resp.raise_for_status()
    data = resp.json()
    return [v["id"] for v in data.get("versions", []) if v.get("type") == "release"]
