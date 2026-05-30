# tests/test_fabric_installer.py
from server_studio.installers.fabric import FabricInstaller


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


def test_install_downloads_server_launcher(tmp_path):
    game = "1.20.6"
    loader_url = "https://meta.fabricmc.net/v2/versions/loader/1.20.6"
    installer_url = "https://meta.fabricmc.net/v2/versions/installer"
    jar_url = (
        "https://meta.fabricmc.net/v2/versions/loader/1.20.6/0.15.11/1.0.1/server/jar"
    )
    routes = {
        loader_url: FakeResponse(json_data=[
            {"loader": {"version": "0.15.11", "stable": True}},
            {"loader": {"version": "0.15.10", "stable": True}},
        ]),
        installer_url: FakeResponse(json_data=[
            {"version": "1.0.1", "stable": True},
            {"version": "1.0.0", "stable": True},
        ]),
        jar_url: FakeResponse(content=b"FABRICJAR"),
    }
    installer = FabricInstaller(client=FakeClient(routes))
    dest = tmp_path / "server.jar"
    result = installer.install(game, dest)

    assert dest.read_bytes() == b"FABRICJAR"
    assert result.java_major == 21


def test_no_loader_raises(tmp_path):
    loader_url = "https://meta.fabricmc.net/v2/versions/loader/9.9.9"
    routes = {loader_url: FakeResponse(json_data=[])}
    installer = FabricInstaller(client=FakeClient(routes))
    try:
        installer.install("9.9.9", tmp_path / "server.jar")
        assert False, "expected ValueError"
    except ValueError:
        pass
