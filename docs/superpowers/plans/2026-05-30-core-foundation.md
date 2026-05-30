# Server Studio — Plan 1: Core Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Server Studio project and let it create, start, stop, and stream the live console of a Vanilla Minecraft server entirely from Python core (no UI yet).

**Architecture:** A pure-Python core package (`server_studio`) with no UI dependency. An `AppPaths` helper owns the on-disk data layout. A `ServerConfig` dataclass is the serialized `server.json`. A `VanillaInstaller` resolves and downloads the server jar from Mojang's manifest. A `ServerProcess` supervises the Java subprocess and streams console output via a callback. `ServerManager` ties these together (create/list/start/stop). All network and process work is tested against mocks/fakes so the suite runs offline and without Java.

**Tech Stack:** Python 3.12, PySide6 (added later — not in this plan), `httpx`, `pytest`, `pytest-mock`, dataclasses, `subprocess`/threads.

---

### Task 0: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/server_studio/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_smoke.py
import server_studio


def test_package_has_version():
    assert isinstance(server_studio.__version__, str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio'`

- [ ] **Step 3: Create the project files**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "server-studio"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27"]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-mock>=3.14"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# src/server_studio/__init__.py
__version__ = "0.1.0"
```

```python
# tests/__init__.py
```

- [ ] **Step 4: Install dev deps and run the test**

Run: `python -m pip install -e ".[dev]"` then `python -m pytest tests/test_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/server_studio/__init__.py tests/__init__.py tests/test_smoke.py
git commit -m "chore: scaffold server_studio package with pytest"
```

---

### Task 1: AppPaths — on-disk data layout

**Files:**
- Create: `src/server_studio/paths.py`
- Test: `tests/test_paths.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_paths.py
from pathlib import Path
from server_studio.paths import AppPaths


def test_paths_are_under_root_and_created(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()
    assert paths.servers == tmp_path / "servers"
    assert paths.java == tmp_path / "java"
    assert paths.cache == tmp_path / "cache"
    assert paths.backups == tmp_path / "backups"
    for p in (paths.servers, paths.java, paths.cache, paths.backups):
        assert p.is_dir()


def test_server_dir_is_under_servers(tmp_path):
    paths = AppPaths(root=tmp_path)
    assert paths.server_dir("abc") == tmp_path / "servers" / "abc"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_paths.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.paths'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/paths.py
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    """Owns the on-disk layout for Server Studio data."""

    root: Path

    @property
    def servers(self) -> Path:
        return self.root / "servers"

    @property
    def java(self) -> Path:
        return self.root / "java"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    def server_dir(self, server_id: str) -> Path:
        return self.servers / server_id

    def ensure(self) -> None:
        for path in (self.servers, self.java, self.cache, self.backups):
            path.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_paths.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/paths.py tests/test_paths.py
git commit -m "feat: add AppPaths for on-disk data layout"
```

---

### Task 2: ServerConfig — the server.json model

**Files:**
- Create: `src/server_studio/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from server_studio.config import ServerConfig


def test_roundtrip_to_and_from_dict():
    cfg = ServerConfig(
        id="abc",
        name="My SMP",
        mc_version="1.20.6",
        loader="vanilla",
        ram_mb=4096,
        port=25565,
    )
    data = cfg.to_dict()
    restored = ServerConfig.from_dict(data)
    assert restored == cfg


def test_save_and_load_file(tmp_path):
    cfg = ServerConfig(id="abc", name="My SMP", mc_version="1.20.6", loader="vanilla")
    path = tmp_path / "server.json"
    cfg.save(path)
    assert path.is_file()
    assert ServerConfig.load(path) == cfg


def test_defaults_applied():
    cfg = ServerConfig(id="abc", name="S", mc_version="1.20.6", loader="vanilla")
    assert cfg.ram_mb == 2048
    assert cfg.port == 25565
    assert cfg.installed_content == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.config'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/config.py
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class ServerConfig:
    """Serialized as server.json inside a server's directory."""

    id: str
    name: str
    mc_version: str
    loader: str
    loader_version: str | None = None
    java_runtime: str | None = None
    ram_mb: int = 2048
    port: int = 25565
    installed_content: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ServerConfig":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ServerConfig":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (all three tests)

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/config.py tests/test_config.py
git commit -m "feat: add ServerConfig model with JSON persistence"
```

---

### Task 3: VanillaInstaller — resolve & download the server jar

**Files:**
- Create: `src/server_studio/installers/__init__.py`
- Create: `src/server_studio/installers/vanilla.py`
- Test: `tests/test_vanilla_installer.py`

This task isolates all Mojang-API logic behind a small interface so it can be tested
offline with a fake HTTP client.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vanilla_installer.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vanilla_installer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.installers'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/installers/__init__.py
```

```python
# src/server_studio/installers/vanilla.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"


@dataclass
class InstallResult:
    jar_path: Path
    java_major: int


class VanillaInstaller:
    """Resolves a Vanilla server jar via the Mojang version manifest.

    `client` must expose `.get(url)` returning an object with `.json()`,
    `.content`, and `.raise_for_status()` (httpx.Client is compatible).
    """

    def __init__(self, client):
        self._client = client

    def _version_url(self, mc_version: str) -> str:
        resp = self._client.get(MANIFEST_URL)
        resp.raise_for_status()
        for entry in resp.json().get("versions", []):
            if entry.get("id") == mc_version:
                return entry["url"]
        raise ValueError(f"Unknown Minecraft version: {mc_version}")

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        version_url = self._version_url(mc_version)
        meta = self._client.get(version_url)
        meta.raise_for_status()
        meta_json = meta.json()
        jar_url = meta_json["downloads"]["server"]["url"]
        java_major = int(meta_json.get("javaVersion", {}).get("majorVersion", 21))

        jar = self._client.get(jar_url)
        jar.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(jar.content)
        return InstallResult(jar_path=dest, java_major=java_major)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vanilla_installer.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/installers/ tests/test_vanilla_installer.py
git commit -m "feat: add VanillaInstaller resolving server jar via Mojang manifest"
```

---

### Task 4: ServerProcess — supervise & stream the Java subprocess

**Files:**
- Create: `src/server_studio/process.py`
- Test: `tests/test_process.py`

Tested against a fake Python child process (no Java needed) that echoes lines, so we can
assert console streaming, command-send, and stop behavior.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_process.py
import sys
import time
from server_studio.process import ServerProcess


# A tiny program that prints "ready", then echoes each stdin line as "echo: <line>".
CHILD_SCRIPT = (
    "import sys\n"
    "print('ready', flush=True)\n"
    "for line in sys.stdin:\n"
    "    sys.stdout.write('echo: ' + line)\n"
    "    sys.stdout.flush()\n"
)


def _wait_for(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_streams_output_and_echoes_commands(tmp_path):
    lines = []
    proc = ServerProcess(
        command=[sys.executable, "-c", CHILD_SCRIPT],
        cwd=tmp_path,
        on_output=lines.append,
    )
    proc.start()
    assert _wait_for(lambda: "ready" in lines)

    proc.send("hello")
    assert _wait_for(lambda: any("echo: hello" in line for line in lines))

    proc.stop()
    assert _wait_for(lambda: not proc.is_running())


def test_is_running_false_before_start(tmp_path):
    proc = ServerProcess(command=[sys.executable, "-c", "pass"], cwd=tmp_path,
                         on_output=lambda _l: None)
    assert proc.is_running() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_process.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.process'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/process.py
from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Callable


class ServerProcess:
    """Runs and supervises a server subprocess, streaming stdout to a callback.

    `on_output` is called once per output line (newline stripped) from a reader
    thread — consumers must be thread-safe or marshal to their UI thread.
    """

    def __init__(self, command: list[str], cwd: Path, on_output: Callable[[str], None]):
        self._command = command
        self._cwd = cwd
        self._on_output = on_output
        self._proc: subprocess.Popen | None = None
        self._reader: threading.Thread | None = None

    def start(self) -> None:
        if self.is_running():
            raise RuntimeError("Process already running")
        self._proc = subprocess.Popen(
            self._command,
            cwd=str(self._cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._reader = threading.Thread(target=self._pump_output, daemon=True)
        self._reader.start()

    def _pump_output(self) -> None:
        assert self._proc and self._proc.stdout
        for line in self._proc.stdout:
            self._on_output(line.rstrip("\n"))

    def send(self, command: str) -> None:
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("Process not running")
        self._proc.stdin.write(command + "\n")
        self._proc.stdin.flush()

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def stop(self, timeout: float = 10.0) -> None:
        if not self._proc:
            return
        # Graceful: Minecraft servers stop on the "stop" command via stdin.
        try:
            if self._proc.stdin and not self._proc.stdin.closed:
                self._proc.stdin.write("stop\n")
                self._proc.stdin.flush()
        except (BrokenPipeError, ValueError):
            pass
        try:
            self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._proc.kill()
```

> Note: the fake child in the test exits when stdin closes after `wait` times out and
> `terminate()` is sent; this exercises the non-graceful path too. The test only asserts
> the process is no longer running after `stop()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_process.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/process.py tests/test_process.py
git commit -m "feat: add ServerProcess to supervise and stream the server subprocess"
```

---

### Task 5: ServerManager — create / list / start / stop

**Files:**
- Create: `src/server_studio/manager.py`
- Test: `tests/test_manager.py`

`ServerManager` is the façade the UI will eventually drive. It depends on `AppPaths`, an
installer (injected), and a process factory (injected) so tests stay offline and
Java-free.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_manager.py
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

    def start(self):
        self.started = True
        self.on_output("Done! Server started")

    def is_running(self):
        return self.started

    def stop(self, timeout=10.0):
        self.started = False


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
        installer=FakeInstaller(),
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
    assert "nogui" in proc.command


def test_stop_marks_not_running(tmp_path):
    mgr, _ = _make_manager(tmp_path)
    cfg = mgr.create_server(name="SMP", mc_version="1.20.6", loader="vanilla")
    mgr.start_server(cfg.id, on_output=lambda _l: None)
    assert mgr.is_running(cfg.id) is True
    mgr.stop_server(cfg.id)
    assert mgr.is_running(cfg.id) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.manager'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/manager.py
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Callable

from server_studio.config import ServerConfig
from server_studio.paths import AppPaths


class ServerManager:
    """Façade for creating and controlling servers.

    Dependencies are injected so the core stays testable offline:
      - installer: object with install(mc_version, dest) -> result(.java_major)
      - process_factory: (command, cwd, on_output) -> process object
        (start(), stop(), is_running())
      - java_resolver: (java_major: int) -> Path to the java executable
    """

    def __init__(self, paths: AppPaths, installer, process_factory: Callable,
                 java_resolver: Callable[[int], Path]):
        self.paths = paths
        self._installer = installer
        self._process_factory = process_factory
        self._java_resolver = java_resolver
        self._running: dict[str, object] = {}

    def create_server(self, name: str, mc_version: str, loader: str,
                      ram_mb: int = 2048, port: int = 25565) -> ServerConfig:
        server_id = uuid.uuid4().hex[:12]
        server_dir = self.paths.server_dir(server_id)
        server_dir.mkdir(parents=True, exist_ok=True)

        result = self._installer.install(mc_version, server_dir / "server.jar")
        (server_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")

        cfg = ServerConfig(
            id=server_id,
            name=name,
            mc_version=mc_version,
            loader=loader,
            java_runtime=f"temurin-{result.java_major}",
            ram_mb=ram_mb,
            port=port,
        )
        cfg.save(server_dir / "server.json")
        return cfg

    def list_servers(self) -> list[ServerConfig]:
        if not self.paths.servers.is_dir():
            return []
        configs = []
        for child in self.paths.servers.iterdir():
            cfg_path = child / "server.json"
            if cfg_path.is_file():
                configs.append(ServerConfig.load(cfg_path))
        return configs

    def get(self, server_id: str) -> ServerConfig:
        return ServerConfig.load(self.paths.server_dir(server_id) / "server.json")

    def _java_major(self, cfg: ServerConfig) -> int:
        runtime = cfg.java_runtime or "temurin-21"
        return int(runtime.split("-")[-1])

    def start_server(self, server_id: str, on_output: Callable[[str], None]) -> None:
        cfg = self.get(server_id)
        server_dir = self.paths.server_dir(server_id)
        java = self._java_resolver(self._java_major(cfg))
        command = [
            str(java),
            f"-Xmx{cfg.ram_mb}M",
            f"-Xms{min(cfg.ram_mb, 1024)}M",
            "-jar",
            "server.jar",
            "nogui",
        ]
        proc = self._process_factory(command, server_dir, on_output)
        proc.start()
        self._running[server_id] = proc

    def is_running(self, server_id: str) -> bool:
        proc = self._running.get(server_id)
        return bool(proc and proc.is_running())

    def stop_server(self, server_id: str) -> None:
        proc = self._running.get(server_id)
        if proc:
            proc.stop()
            self._running.pop(server_id, None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_manager.py -v`
Expected: PASS (all four tests)

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/manager.py tests/test_manager.py
git commit -m "feat: add ServerManager facade (create/list/start/stop)"
```

---

### Task 6: Full suite green + README note

**Files:**
- Create: `README.md`
- Test: (whole suite)

- [ ] **Step 1: Run the full suite**

Run: `python -m pytest -v`
Expected: PASS — all tests from Tasks 0–5 green.

- [ ] **Step 2: Write the README**

```markdown
# Server Studio

Create and manage local Minecraft servers with a modern desktop UI.

## Status
Plan 1 (Core Foundation) — pure-Python core that can create, start, stop, and stream a
Vanilla server. UI, loaders, mod browser, tunnel, and backups arrive in later plans.

## Development
```
python -m pip install -e ".[dev]"
python -m pytest
```
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README for Plan 1 core foundation"
```

---

## What's NOT in this plan (future plans, one each)

- **Plan 2 — Versions & Java:** VersionManager (Paper/Purpur/Fabric/Forge/NeoForge/Spigot)
  + JavaManager (auto-download Temurin from Adoptium, the real `java_resolver`).
- **Plan 3 — Mod/Plugin Browser:** Modrinth (version+loader filtered) + manual import +
  enable/disable/update/remove; then CurseForge.
- **Plan 4 — Tunnel:** one-click internet sharing + LAN/port-forward info.
- **Plan 5 — Backups:** snapshot/restore worlds.
- **Plan 6 — UI:** PySide6 dashboard, new-server wizard, server detail tabs, theming +
  animations.
- **Plan 7 — Packaging:** PyInstaller `.exe`, first-run experience, distribution.

## Self-Review Notes

- **Spec coverage (this plan):** Covers ServerManager create/start/stop/console + Vanilla
  install + the on-disk data layout & `server.json` from the spec. Remaining spec
  subsystems are explicitly deferred to Plans 2–7 above.
- **Injected `java_resolver`:** Plan 1 injects a stub resolver in tests; the real
  Adoptium-backed resolver is delivered in Plan 2 (JavaManager). Until then a manually
  installed Java path can be supplied.
- **Type consistency:** `ServerConfig` fields, `InstallResult.java_major`, and
  `ServerProcess(command, cwd, on_output)` signatures are used consistently across
  installer, process, and manager tasks.
