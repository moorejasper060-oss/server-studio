# src/server_studio/installers/curseforge.py
from __future__ import annotations

import os
from dataclasses import dataclass

API = "https://api.curseforge.com/v1"
_LOADER_TYPE = {"forge": 1, "fabric": 4, "quilt": 5, "neoforge": 6}


@dataclass
class ModResult:
    project_id: str
    slug: str
    title: str
    description: str
    downloads: int


class CurseForgeClient:
    """Searches CurseForge (requires an API key)."""

    def __init__(self, client, api_key: str):
        self._client = client
        self._api_key = api_key

    @classmethod
    def from_env(cls, client) -> "CurseForgeClient | None":
        key = os.environ.get("CURSEFORGE_API_KEY")
        return cls(client=client, api_key=key) if key else None

    def search(self, query: str, mc_version: str, loader: str) -> list[ModResult]:
        params = {"gameId": 432, "searchFilter": query, "gameVersion": mc_version}
        loader_type = _LOADER_TYPE.get(loader.lower())
        if loader_type is not None:
            params["modLoaderType"] = loader_type
        resp = self._client.get(f"{API}/mods/search", params=params,
                                headers={"x-api-key": self._api_key})
        resp.raise_for_status()
        out = []
        for mod in resp.json().get("data", []):
            out.append(ModResult(
                project_id=str(mod["id"]), slug=mod["slug"], title=mod["name"],
                description=mod.get("summary", ""), downloads=mod.get("downloadCount", 0),
            ))
        return out
