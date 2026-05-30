import json
from server_studio.installers.vanilla import VanillaInstaller


class FakeResponse:
    def __init__(self, *, json_data=None, content=b""):
        self._json = json_data
        self.content = content

    def json(self):
        return self._json

    def raise_for_status(self):
        return None


class FakeClient:
    """Maps URLs to FakeResponse objects."""

    def __init__(self, routes):
        self.routes = routes
        self.requested = []

    def get(self, url):
        self.requested.append(url)
        return self.routes[url]


def test_install_downloads_jar_for_version(tmp_path):
    manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
    version_url = "https://example/1.20.6.json"
    jar_url = "https://example/server.jar"

    routes = {
        manifest_url: FakeResponse(json_data={
            "versions": [{"id": "1.20.6", "url": version_url}],
        }),
        version_url: FakeResponse(json_data={
            "downloads": {"server": {"url": jar_url}},
            "javaVersion": {"majorVersion": 21},
        }),
        jar_url: FakeResponse(content=b"JARBYTES"),
    }
    client = FakeClient(routes)
    installer = VanillaInstaller(client=client)

    dest = tmp_path / "server.jar"
    result = installer.install("1.20.6", dest)

    assert dest.read_bytes() == b"JARBYTES"
    assert result.java_major == 21


def test_unknown_version_raises(tmp_path):
    manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
    routes = {manifest_url: FakeResponse(json_data={"versions": []})}
    installer = VanillaInstaller(client=FakeClient(routes))
    try:
        installer.install("9.9.9", tmp_path / "server.jar")
        assert False, "expected ValueError"
    except ValueError:
        pass
