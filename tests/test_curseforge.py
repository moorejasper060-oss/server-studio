from server_studio.installers.curseforge import CurseForgeClient, ModResult


class FakeResponse:
    def __init__(self, json_data):
        self._json = json_data
    def json(self): return self._json
    def raise_for_status(self): return None


class FakeClient:
    def __init__(self, routes):
        self.routes = routes
        self.headers_seen = []
    def get(self, url, params=None, headers=None):
        self.headers_seen.append(headers)
        return self.routes[url]


def test_search_sends_api_key_and_filters():
    url = "https://api.curseforge.com/v1/mods/search"
    routes = {url: FakeResponse({"data": [
        {"id": 12345, "slug": "jei", "name": "JEI", "summary": "items",
         "downloadCount": 50000000},
    ]})}
    client = FakeClient(routes)
    cf = CurseForgeClient(client=client, api_key="KEY123")
    results = cf.search("jei", mc_version="1.20.6", loader="forge")
    assert results[0] == ModResult(project_id="12345", slug="jei", title="JEI",
                                   description="items", downloads=50000000)
    assert client.headers_seen[0]["x-api-key"] == "KEY123"


def test_from_env_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("CURSEFORGE_API_KEY", raising=False)
    assert CurseForgeClient.from_env(client=object()) is None


def test_from_env_builds_with_key(monkeypatch):
    monkeypatch.setenv("CURSEFORGE_API_KEY", "ABC")
    cf = CurseForgeClient.from_env(client=object())
    assert isinstance(cf, CurseForgeClient)
