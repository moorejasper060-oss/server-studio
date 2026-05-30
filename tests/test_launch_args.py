# tests/test_launch_args.py
from pathlib import Path
from server_studio.installers.base import InstallResult
from server_studio.config import ServerConfig
from server_studio.paths import AppPaths
from server_studio.manager import ServerManager


def test_install_result_defaults_to_jar_launch():
    r = InstallResult(jar_path=Path("x/server.jar"), java_major=21)
    assert r.launch_args == ["-jar", "server.jar", "nogui"]


def test_install_result_accepts_custom_launch():
    r = InstallResult(jar_path=Path("x"), java_major=21,
                      launch_args=["@libraries/a/win_args.txt", "nogui"])
    assert r.launch_args == ["@libraries/a/win_args.txt", "nogui"]


def test_server_config_roundtrips_launch_args(tmp_path):
    cfg = ServerConfig(id="a", name="N", mc_version="1.20.6", loader="forge",
                       launch_args=["@libraries/x/win_args.txt", "nogui"])
    path = tmp_path / "server.json"
    cfg.save(path)
    assert ServerConfig.load(path).launch_args == ["@libraries/x/win_args.txt", "nogui"]


def test_server_config_default_launch_args():
    cfg = ServerConfig(id="a", name="N", mc_version="1.20.6", loader="vanilla")
    assert cfg.launch_args == ["-jar", "server.jar", "nogui"]


class _Result:
    def __init__(self, launch_args):
        self.java_major = 21
        self.launch_args = launch_args


class FakeInstaller:
    def __init__(self, launch_args):
        self._la = launch_args
    def install(self, mc_version, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"X")
        return _Result(self._la)


class FakeProc:
    def __init__(self, command, cwd, on_output):
        self.command = command
    def start(self): pass
    def is_running(self): return True
    def stop(self, timeout=10.0): pass


def test_start_uses_config_launch_args(tmp_path):
    paths = AppPaths(root=tmp_path); paths.ensure()
    created = []
    def factory(command, cwd, on_output):
        p = FakeProc(command, cwd, on_output); created.append(p); return p
    mgr = ServerManager(
        paths=paths,
        installer_for=lambda loader: FakeInstaller(["@libraries/x/win_args.txt", "nogui"]),
        process_factory=factory,
        java_resolver=lambda major: Path(f"/java/{major}/bin/java"),
    )
    cfg = mgr.create_server(name="F", mc_version="1.20.6", loader="forge", ram_mb=4096)
    assert cfg.launch_args == ["@libraries/x/win_args.txt", "nogui"]
    mgr.start_server(cfg.id, on_output=lambda _l: None)
    cmd = created[-1].command
    assert "-Xmx4096M" in cmd
    assert "@libraries/x/win_args.txt" in cmd
    assert "-jar" not in cmd
