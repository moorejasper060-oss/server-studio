import uuid
from pathlib import Path
from server_studio.config import ServerConfig
from server_studio.paths import AppPaths
from server_studio.manager import ServerManager


class FakeInstaller:
    def __init__(self):
        self.calls = []

    def install(self, mc_version, dest: Path):
        self.calls.append((mc_version, dest))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"FAKEJAR")

        class _R:
            java_major = 21
        return _R()


class FakeProcess:
    def __init__(self, command, cwd, on_output):
        self.command = command
        self.cwd = cwd
        self.on_output = on_output
        self.started = False
        self.sent = []

    def start(self):
        self.started = True
        self.on_output("Done! Server started")

    def is_running(self):
        return self.started

    def stop(self, timeout=10.0):
        self.started = False

    def send(self, command):
        self.sent.append(command)


def _make_manager(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()
    created = []

    def factory(command, cwd, on_output):
        proc = FakeProcess(command, cwd, on_output)
        created.append(proc)
        return proc

    mgr = ServerManager(
        paths=paths,
        installer_for=lambda loader: FakeInstaller(),
        process_factory=factory,
        java_resolver=lambda major: Path(f"/java/{major}/bin/java"),
    )
    return mgr, created


def test_create_writes_config_and_jar(tmp_path):
    mgr, _ = _make_manager(tmp_path)
    cfg = mgr.create_server(name="SMP", mc_version="1.20.6", loader="vanilla", ram_mb=4096)
    server_dir = mgr.paths.server_dir(cfg.id)
    assert (server_dir / "server.json").is_file()
    assert (server_dir / "server.jar").read_bytes() == b"FAKEJAR"
    assert (server_dir / "eula.txt").read_text(encoding="utf-8").strip() == "eula=true"
    assert cfg.ram_mb == 4096


def test_list_servers_returns_created(tmp_path):
    mgr, _ = _make_manager(tmp_path)
    mgr.create_server(name="A", mc_version="1.20.6", loader="vanilla")
    mgr.create_server(name="B", mc_version="1.20.6", loader="vanilla")
    names = sorted(c.name for c in mgr.list_servers())
    assert names == ["A", "B"]


def test_start_uses_java_and_ram_flags(tmp_path):
    mgr, created = _make_manager(tmp_path)
    cfg = mgr.create_server(name="SMP", mc_version="1.20.6", loader="vanilla", ram_mb=3072)
    mgr.start_server(cfg.id, on_output=lambda _l: None)
    proc = created[-1]
    assert proc.started is True
    assert str(Path("/java/21/bin/java")) in proc.command
    assert "-Xmx3072M" in proc.command
    assert "-Xms1024M" in proc.command
    assert "nogui" in proc.command


def test_stop_marks_not_running(tmp_path):
    mgr, _ = _make_manager(tmp_path)
    cfg = mgr.create_server(name="SMP", mc_version="1.20.6", loader="vanilla")
    mgr.start_server(cfg.id, on_output=lambda _l: None)
    assert mgr.is_running(cfg.id) is True
    mgr.stop_server(cfg.id)
    assert mgr.is_running(cfg.id) is False


def test_start_twice_raises(tmp_path):
    mgr, _ = _make_manager(tmp_path)
    cfg = mgr.create_server(name="SMP", mc_version="1.20.6", loader="vanilla")
    mgr.start_server(cfg.id, on_output=lambda _l: None)
    try:
        mgr.start_server(cfg.id, on_output=lambda _l: None)
        assert False, "expected RuntimeError on double start"
    except RuntimeError:
        pass


def test_send_command_forwards_to_running_process(tmp_path):
    mgr, created = _make_manager(tmp_path)
    cfg = mgr.create_server(name="SMP", mc_version="1.20.6", loader="vanilla")
    mgr.start_server(cfg.id, on_output=lambda _l: None)
    mgr.send_command(cfg.id, "say hello")
    assert created[-1].sent == ["say hello"]


def test_send_command_when_not_running_raises(tmp_path):
    mgr, _ = _make_manager(tmp_path)
    cfg = mgr.create_server(name="SMP", mc_version="1.20.6", loader="vanilla")
    try:
        mgr.send_command(cfg.id, "say hi")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
