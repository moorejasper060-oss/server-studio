from __future__ import annotations

import json
from dataclasses import dataclass

API = "https://api.modrinth.com/v2"


@dataclass
class ModResult:
    project_id: str
    slug: str
    title: str
    description: str
    downloads: int


@dataclass
class ModFile:
    version_id: str
    filename: str
    url: str


class ModrinthClient:
    """Searches Modrinth filtered to a server's MC version + loader."""

    def __init__(self, client):
        self._client = client

    def search(self, query: str, mc_version: str, loader: str) -> list[ModResult]:
        facets = json.dumps([[f"versions:{mc_version}"], [f"categories:{loader}"]])
        resp = self._client.get(f"{API}/search", params={"query": query, "facets": facets})
        resp.raise_for_status()
        out = []
        for hit in resp.json().get("hits", []):
            out.append(ModResult(
                project_id=hit["project_id"], slug=hit["slug"], title=hit["title"],
                description=hit.get("description", ""), downloads=hit.get("downloads", 0),
            ))
        return out

    def get_files(self, project_id: str, mc_version: str, loader: str) -> list[ModFile]:
        params = {
            "game_versions": json.dumps([mc_version]),
            "loaders": json.dumps([loader]),
        }
        resp = self._client.get(f"{API}/project/{project_id}/version", params=params)
        resp.raise_for_status()
        out = []
        for version in resp.json():
            primary = next((f for f in version["files"] if f.get("primary")),
                           version["files"][0] if version["files"] else None)
            if primary:
                out.append(ModFile(version_id=version["id"],
                                   filename=primary["filename"], url=primary["url"]))
        return out
