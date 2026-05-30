# tests/test_spigot_installer.py
from server_studio.installers.spigot import SpigotInstaller


class FakeResponse:
    def __init__(self, *, content=b""):
        self.content = content
    def raise_for_status(self): return None


class FakeClient:
    def __init__(self, routes):
        self.routes = routes
        self.requested = []
    def get(self, url):
        self.requested.append(url)
        return self.routes[url]


BUILDTOOLS_URL = (
    "https://hub.spigotmc.org/jenkins/job/BuildTools/"
    "lastSuccessfulBuild/artifact/target/BuildTools.jar"
)


def test_install_builds_and_copies(tmp_path):
    routes = {BUILDTOOLS_URL: FakeResponse(content=b"BUILDTOOLS")}
    client = FakeClient(routes)
    runner_calls = []

    def fake_runner(command, cwd):
        runner_calls.append((command, cwd))
        (cwd / "spigot-1.20.6.jar").write_bytes(b"SPIGOTJAR")

    installer = SpigotInstaller(client=client,
                                java_resolver=lambda m: f"/java/{m}/bin/java",
                                runner=fake_runner)
    server_dir = tmp_path / "srv"; server_dir.mkdir()
    result = installer.install("1.20.6", server_dir / "server.jar")

    assert (server_dir / "server.jar").read_bytes() == b"SPIGOTJAR"
    assert "--rev" in runner_calls[0][0]
    assert "1.20.6" in runner_calls[0][0]
    assert result.java_major == 21
    assert result.launch_args == ["-jar", "server.jar", "nogui"]


def test_missing_built_jar_raises(tmp_path):
    routes = {BUILDTOOLS_URL: FakeResponse(content=b"BUILDTOOLS")}
    installer = SpigotInstaller(client=FakeClient(routes),
                                java_resolver=lambda m: "/java",
                                runner=lambda c, d: None)
    server_dir = tmp_path / "srv"; server_dir.mkdir()
    try:
        installer.install("1.20.6", server_dir / "server.jar")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
