# src/server_studio/ui/content_service.py
from __future__ import annotations


class ContentService:
    """Adapts a ModrinthClient + ContentManager to the ModsTab service interface."""

    def __init__(self, server_id, mc_version, loader, search_client, content):
        self._sid = server_id
        self._mc = mc_version
        self._loader = loader
        self._search = search_client
        self._content = content

    def search(self, query: str) -> list[dict]:
        results = self._search.search(query, self._mc, self._loader)
        return [{"project_id": r.project_id, "title": r.title,
                 "description": r.description, "slug": r.slug} for r in results]

    def install(self, result: dict) -> None:
        files = self._search.get_files(result["project_id"], self._mc, self._loader)
        if not files:
            raise ValueError(f"No compatible file for {result['title']}")
        f = files[0]
        self._content.install(self._sid, source="modrinth",
                              project_id=result["project_id"], version_id=f.version_id,
                              filename=f.filename, url=f.url)

    def list_installed(self) -> list[dict]:
        return self._content.list_installed(self._sid)

    def set_enabled(self, filename: str, enabled: bool) -> None:
        self._content.set_enabled(self._sid, filename, enabled)

    def remove(self, filename: str) -> None:
        self._content.remove(self._sid, filename)
