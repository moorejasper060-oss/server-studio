# tests/test_forge_installer.py
from server_studio.installers.forge import ForgeInstaller


class FakeResponse:
    def __init__(self, *, json_data=None, content=b""):
        self._json = json_data
        self.content = content
    def json(self): return self._json
    def raise_for_status(self): return None


class FakeClient:
    def __init__(self, routes):
        self.routes = routes
        self.requested = []
    def get(self, url):
        self.requested.append(url)
        return self.routes[url]


def test_install_downloads_runs_and_detects(tmp_path):
    promos = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
    full = "1.20.6-50.1.0"
    installer_url = (
        "https://maven.minecraftforge.net/net/minecraftforge/forge/"
        f"{full}/forge-{full}-installer.jar"
    )
    routes = {
        promos: FakeResponse(json_data={"promos": {"1.20.6-recommended": "50.1.0"}}),
        installer_url: FakeResponse(content=b"INSTALLER"),
    }
    client = FakeClient(routes)

    runner_calls = []

    def fake_runner(command, cwd):
        runner_calls.append((command, cwd))
        d = cwd / "libraries" / "net" / "minecraftforge" / "forge" / full
        d.mkdir(parents=True)
        (d / "win_args.txt").write_text("@x", encoding="utf-8")

    installer = ForgeInstaller(client=client,
                               java_resolver=lambda major: f"/java/{major}/bin/java",
                               runner=fake_runner)
    server_dir = tmp_path / "srv"; server_dir.mkdir()
    result = installer.install("1.20.6", server_dir / "server.jar")

    assert (server_dir / "forge-installer.jar").read_bytes() == b"INSTALLER"
    assert "--installServer" in runner_calls[0][0]
    assert result.java_major == 21
    assert result.launch_args == [
        f"@libraries/net/minecraftforge/forge/{full}/win_args.txt", "nogui",
    ]


def test_unknown_version_raises(tmp_path):
    promos = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
    routes = {promos: FakeResponse(json_data={"promos": {}})}
    installer = ForgeInstaller(client=FakeClient(routes),
                               java_resolver=lambda m: "/java", runner=lambda c, d: None)
    try:
        installer.install("9.9.9", tmp_path / "server.jar")
        assert False, "expected ValueError"
    except ValueError:
        pass
