# tests/test_neoforge_installer.py
from server_studio.installers.neoforge import NeoForgeInstaller, neoforge_prefix


class FakeResponse:
    def __init__(self, *, text="", content=b""):
        self.text = text
        self.content = content
    def raise_for_status(self): return None


class FakeClient:
    def __init__(self, routes):
        self.routes = routes
        self.requested = []
    def get(self, url):
        self.requested.append(url)
        return self.routes[url]


def test_prefix_mapping():
    assert neoforge_prefix("1.20.6") == "20.6"
    assert neoforge_prefix("1.21") == "21.0"
    assert neoforge_prefix("1.21.4") == "21.4"


METADATA_URL = "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml"

METADATA_XML = """<?xml version="1.0"?>
<metadata><versioning><versions>
<version>20.6.50</version>
<version>20.6.119</version>
<version>21.0.1</version>
</versions></versioning></metadata>"""


def test_install_picks_highest_matching_and_runs(tmp_path):
    ver = "20.6.119"
    installer_url = (
        "https://maven.neoforged.net/releases/net/neoforged/neoforge/"
        f"{ver}/neoforge-{ver}-installer.jar"
    )
    routes = {
        METADATA_URL: FakeResponse(text=METADATA_XML),
        installer_url: FakeResponse(content=b"NEO"),
    }
    client = FakeClient(routes)

    def fake_runner(command, cwd):
        d = cwd / "libraries" / "net" / "neoforged" / "neoforge" / ver
        d.mkdir(parents=True)
        (d / "win_args.txt").write_text("@x", encoding="utf-8")

    installer = NeoForgeInstaller(client=client,
                                  java_resolver=lambda m: f"/java/{m}/bin/java",
                                  runner=fake_runner)
    server_dir = tmp_path / "srv"; server_dir.mkdir()
    result = installer.install("1.20.6", server_dir / "server.jar")

    assert (server_dir / "neoforge-installer.jar").read_bytes() == b"NEO"
    assert result.launch_args == [
        f"@libraries/net/neoforged/neoforge/{ver}/win_args.txt", "nogui",
    ]


def test_no_matching_version_raises(tmp_path):
    routes = {METADATA_URL: FakeResponse(text=METADATA_XML)}
    installer = NeoForgeInstaller(client=FakeClient(routes),
                                  java_resolver=lambda m: "/java", runner=lambda c, d: None)
    try:
        installer.install("1.19.2", tmp_path / "server.jar")
        assert False, "expected ValueError"
    except ValueError:
        pass


METADATA_WITH_BETAS = """<?xml version="1.0"?>
<metadata><versioning><versions>
<version>20.4.0-beta</version>
<version>20.4.236</version>
<version>20.4.80-beta</version>
</versions></versioning></metadata>"""


def test_prefers_stable_over_beta(tmp_path):
    ver = "20.4.236"
    installer_url = (
        "https://maven.neoforged.net/releases/net/neoforged/neoforge/"
        f"{ver}/neoforge-{ver}-installer.jar"
    )
    routes = {
        METADATA_URL: FakeResponse(text=METADATA_WITH_BETAS),
        installer_url: FakeResponse(content=b"NEO"),
    }
    def fake_runner(command, cwd):
        d = cwd / "libraries" / "net" / "neoforged" / "neoforge" / ver
        d.mkdir(parents=True)
        (d / "win_args.txt").write_text("@x", encoding="utf-8")
    installer = NeoForgeInstaller(client=FakeClient(routes),
                                  java_resolver=lambda m: f"/java/{m}/bin/java",
                                  runner=fake_runner)
    server_dir = tmp_path / "srv"; server_dir.mkdir()
    result = installer.install("1.20.4", server_dir / "server.jar")
    assert (server_dir / "neoforge-installer.jar").read_bytes() == b"NEO"   # picked 20.4.236, not a beta
    assert "20.4.236" in result.launch_args[0]


def test_picks_highest_beta_when_only_betas(tmp_path):
    xml = ("<?xml version='1.0'?><metadata><versioning><versions>"
           "<version>20.4.0-beta</version><version>20.4.80-beta</version>"
           "</versions></versioning></metadata>")
    ver = "20.4.80-beta"
    installer_url = (
        "https://maven.neoforged.net/releases/net/neoforged/neoforge/"
        f"{ver}/neoforge-{ver}-installer.jar"
    )
    routes = {
        METADATA_URL: FakeResponse(text=xml),
        installer_url: FakeResponse(content=b"NEO"),
    }
    def fake_runner(command, cwd):
        d = cwd / "libraries" / "net" / "neoforged" / "neoforge" / ver
        d.mkdir(parents=True)
        (d / "win_args.txt").write_text("@x", encoding="utf-8")
    installer = NeoForgeInstaller(client=FakeClient(routes),
                                  java_resolver=lambda m: "/java", runner=fake_runner)
    server_dir = tmp_path / "srv"; server_dir.mkdir()
    result = installer.install("1.20.4", server_dir / "server.jar")
    assert "20.4.80-beta" in result.launch_args[0]
