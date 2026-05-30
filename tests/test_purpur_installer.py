# tests/test_purpur_installer.py
from server_studio.installers.purpur import PurpurInstaller


class FakeResponse:
    def __init__(self, *, json_data=None, content=b""):
        self._json = json_data
        self.content = content

    def json(self):
        return self._json

    def raise_for_status(self):
        return None


class FakeClient:
    def __init__(self, routes):
        self.routes = routes
        self.requested = []

    def get(self, url):
        self.requested.append(url)
        return self.routes[url]


def test_install_downloads_latest_build(tmp_path):
    meta_url = "https://api.purpurmc.org/v2/purpur/1.20.4"
    download_url = "https://api.purpurmc.org/v2/purpur/1.20.4/2150/download"
    routes = {
        meta_url: FakeResponse(json_data={"builds": {"latest": "2150"}}),
        download_url: FakeResponse(content=b"PURPURJAR"),
    }
    installer = PurpurInstaller(client=FakeClient(routes))
    dest = tmp_path / "server.jar"
    result = installer.install("1.20.4", dest)

    assert dest.read_bytes() == b"PURPURJAR"
    assert result.java_major == 17  # 1.20.4 → Java 17


def test_missing_latest_raises(tmp_path):
    meta_url = "https://api.purpurmc.org/v2/purpur/1.20.4"
    routes = {meta_url: FakeResponse(json_data={"builds": {}})}
    installer = PurpurInstaller(client=FakeClient(routes))
    try:
        installer.install("1.20.4", tmp_path / "server.jar")
        assert False, "expected ValueError"
    except ValueError:
        pass
