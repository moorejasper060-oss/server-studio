import json
from server_studio.installers.modrinth import ModrinthClient, ModResult, ModFile


class FakeResponse:
    def __init__(self, *, json_data=None, content=b""):
        self._json = json_data
        self.content = content
    def json(self): return self._json
    def raise_for_status(self): return None


class FakeClient:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []
    def get(self, url, params=None):
        self.calls.append((url, params))
        # match on url; params encoded by caller for facets
        return self.routes[url]


def test_search_filters_by_version_and_loader():
    url = "https://api.modrinth.com/v2/search"
    routes = {url: FakeResponse(json_data={"hits": [
        {"project_id": "AABB", "slug": "sodium", "title": "Sodium",
         "description": "perf", "downloads": 1000000},
    ]})}
    client = FakeClient(routes)
    mc = ModrinthClient(client=client)
    results = mc.search("sodium", mc_version="1.20.6", loader="fabric")
    assert results[0] == ModResult(project_id="AABB", slug="sodium", title="Sodium",
                                   description="perf", downloads=1000000)
    # facets must include both the version and the loader
    _, params = client.calls[0]
    facets = json.loads(params["facets"])
    assert ["versions:1.20.6"] in facets
    assert ["categories:fabric"] in facets


def test_get_files_returns_compatible_downloads():
    pid = "AABB"
    url = f"https://api.modrinth.com/v2/project/{pid}/version"
    routes = {url: FakeResponse(json_data=[
        {"id": "v1", "files": [
            {"filename": "sodium-1.20.6.jar", "url": "https://cdn/sodium.jar", "primary": True},
        ], "dependencies": []},
    ])}
    mc = ModrinthClient(client=FakeClient(routes))
    files = mc.get_files(pid, mc_version="1.20.6", loader="fabric")
    assert files[0] == ModFile(version_id="v1", filename="sodium-1.20.6.jar",
                               url="https://cdn/sodium.jar")
