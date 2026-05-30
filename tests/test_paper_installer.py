# tests/test_paper_installer.py
from server_studio.installers.paper import PaperInstaller


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


def test_install_downloads_latest_build_jar(tmp_path):
    version = "1.20.6"
    builds_url = "https://api.papermc.io/v2/projects/paper/versions/1.20.6"
    build_url = "https://api.papermc.io/v2/projects/paper/versions/1.20.6/builds/147"
    jar_name = "paper-1.20.6-147.jar"
    download_url = (
        "https://api.papermc.io/v2/projects/paper/versions/1.20.6/builds/147/downloads/"
        + jar_name
    )
    routes = {
        builds_url: FakeResponse(json_data={"builds": [120, 147, 130]}),
        build_url: FakeResponse(json_data={
            "downloads": {"application": {"name": jar_name}},
        }),
        download_url: FakeResponse(content=b"PAPERJAR"),
    }
    installer = PaperInstaller(client=FakeClient(routes))
    dest = tmp_path / "server.jar"
    result = installer.install(version, dest)

    assert dest.read_bytes() == b"PAPERJAR"
    assert result.java_major == 21  # 1.20.6 → Java 21


def test_no_builds_raises(tmp_path):
    builds_url = "https://api.papermc.io/v2/projects/paper/versions/1.20.6"
    routes = {builds_url: FakeResponse(json_data={"builds": []})}
    installer = PaperInstaller(client=FakeClient(routes))
    try:
        installer.install("1.20.6", tmp_path / "server.jar")
        assert False, "expected ValueError"
    except ValueError:
        pass
