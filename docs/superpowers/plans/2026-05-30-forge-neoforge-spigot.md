# Server Studio — Plan 2b: Forge / NeoForge / Spigot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the three installer-process-based loaders — Forge, NeoForge (run a Java installer jar that produces an `@args.txt` launch) and Spigot (compile via BuildTools) — and generalize the launch command so any loader can specify how it boots.

**Architecture:** Generalize launch: `InstallResult` and `ServerConfig` gain `launch_args` (what follows the `-Xmx/-Xms` flags); `ServerManager.start_server` uses it (default stays `-jar server.jar nogui`, so existing loaders are unchanged). Three new installers run a Java subprocess during install; they take an injected HTTP client (downloads), a `java_resolver` (the JavaManager resolver — they need a JDK to run the installer/BuildTools), and a `runner` (subprocess executor) so the whole suite stays offline. A pure `detect_launch_args(server_dir)` figures out Forge/NeoForge's launch from the files the installer produced.

**Tech Stack:** Python, `httpx` (faked in tests), `xml.etree` (NeoForge maven metadata), `subprocess` (the real runner). Real endpoints: Forge promotions + maven, NeoForge maven, Spigot BuildTools.

**Deferred / risk:** The exact maven/promotions URLs and the produced-file layout are verified against live services only in manual QA (Task 9) — all network + process work is injected, so unit tests prove the logic, not the endpoints.

---

### Task 1: Generalize the launch command (`launch_args`)

**Files:**
- Modify: `src/server_studio/installers/base.py`
- Modify: `src/server_studio/config.py`
- Modify: `src/server_studio/manager.py`
- Test: `tests/test_launch_args.py`

- [ ] **Step 1: Write the failing test**

```python
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
    assert "-jar" not in cmd  # forge does not use -jar
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_launch_args.py -v`
Expected: FAIL — `InstallResult.__init__() got an unexpected keyword argument 'launch_args'`.

- [ ] **Step 3: Write minimal implementation**

In `src/server_studio/installers/base.py`, add `field` import and the `launch_args` field:

```python
# src/server_studio/installers/base.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


def _default_launch_args() -> list[str]:
    return ["-jar", "server.jar", "nogui"]


@dataclass
class InstallResult:
    jar_path: Path
    java_major: int
    launch_args: list[str] = field(default_factory=_default_launch_args)


@runtime_checkable
class Installer(Protocol):
    """A loader installer: download/produce the runnable server in `dest`'s directory."""

    def install(self, mc_version: str, dest: Path) -> InstallResult: ...
```

In `src/server_studio/config.py`, add the field to `ServerConfig` (after `installed_content`):

```python
    launch_args: list[str] = field(default_factory=lambda: ["-jar", "server.jar", "nogui"])
```

In `src/server_studio/manager.py`:
- In `create_server`, pass `launch_args=result.launch_args` to the `ServerConfig(...)` call.
- In `start_server`, replace the hard-coded command tail. The command becomes:

```python
        command = [
            str(java),
            f"-Xmx{cfg.ram_mb}M",
            f"-Xms{min(cfg.ram_mb, 1024)}M",
            *cfg.launch_args,
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_launch_args.py tests/test_manager.py tests/test_config.py tests/test_installer_base.py -v`
Expected: PASS — new tests pass AND existing manager/config/installer-base tests still pass (defaults keep `-jar server.jar nogui`).

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/installers/base.py src/server_studio/config.py src/server_studio/manager.py tests/test_launch_args.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: generalize server launch via launch_args"
```

---

### Task 2: Subprocess runner

**Files:**
- Create: `src/server_studio/installers/runner.py`
- Test: `tests/test_runner.py`

The real executor for installer/BuildTools processes. Injected into the process-based
installers so tests use a fake. Tested here against a real short Python child.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_runner.py
import sys
from server_studio.installers.runner import run_process


def test_run_process_succeeds(tmp_path):
    # Writes a marker file; returns None on success.
    run_process([sys.executable, "-c", "open('ok.txt','w').write('hi')"], cwd=tmp_path)
    assert (tmp_path / "ok.txt").read_text() == "hi"


def test_run_process_raises_on_nonzero(tmp_path):
    try:
        run_process([sys.executable, "-c", "import sys; sys.exit(3)"], cwd=tmp_path)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "3" in str(exc)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.installers.runner'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/installers/runner.py
from __future__ import annotations

import subprocess
from pathlib import Path


def run_process(command: list[str], cwd: Path) -> None:
    """Run a command to completion in `cwd`; raise RuntimeError on non-zero exit."""
    result = subprocess.run(
        [str(c) for c in command],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        tail = (result.stdout or "")[-500:] + (result.stderr or "")[-500:]
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): {' '.join(map(str, command))}\n{tail}"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_runner.py -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/installers/runner.py tests/test_runner.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: add subprocess runner for installer processes"
```

---

### Task 3: Forge/NeoForge launch detection

**Files:**
- Create: `src/server_studio/installers/launch_detect.py`
- Test: `tests/test_launch_detect.py`

Pure logic: given the directory a Forge/NeoForge installer populated, work out the launch
args. Modern (1.17+) installers drop a `libraries/.../win_args.txt`; older ones drop a
runnable `forge-<ver>.jar`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_launch_detect.py
from server_studio.installers.launch_detect import detect_launch_args


def test_modern_args_file(tmp_path):
    args = tmp_path / "libraries" / "net" / "minecraftforge" / "forge" / "1.20.6-50.0.0"
    args.mkdir(parents=True)
    (args / "win_args.txt").write_text("@stuff", encoding="utf-8")
    result = detect_launch_args(tmp_path)
    assert result == [
        "@libraries/net/minecraftforge/forge/1.20.6-50.0.0/win_args.txt", "nogui",
    ]


def test_legacy_runnable_jar(tmp_path):
    (tmp_path / "forge-1.12.2-14.23.5.2860-universal.jar").write_text("", encoding="utf-8")
    # an installer jar must be ignored
    (tmp_path / "forge-1.12.2-14.23.5.2860-installer.jar").write_text("", encoding="utf-8")
    result = detect_launch_args(tmp_path)
    assert result == ["-jar", "forge-1.12.2-14.23.5.2860-universal.jar", "nogui"]


def test_fallback_to_server_jar(tmp_path):
    assert detect_launch_args(tmp_path) == ["-jar", "server.jar", "nogui"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_launch_detect.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.installers.launch_detect'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/installers/launch_detect.py
from __future__ import annotations

from pathlib import Path


def detect_launch_args(server_dir: Path) -> list[str]:
    """Determine how a Forge/NeoForge install should be launched.

    Modern installers (MC 1.17+) produce libraries/.../win_args.txt; older ones produce
    a runnable forge-<ver>.jar. Falls back to the plain server.jar form.
    """
    args_files = sorted(server_dir.glob("libraries/**/win_args.txt"))
    if args_files:
        rel = args_files[0].relative_to(server_dir).as_posix()
        return [f"@{rel}", "nogui"]

    for pattern in ("forge-*.jar", "neoforge-*.jar"):
        for jar in sorted(server_dir.glob(pattern)):
            if "installer" not in jar.name:
                return ["-jar", jar.name, "nogui"]

    return ["-jar", "server.jar", "nogui"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_launch_detect.py -v`
Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/installers/launch_detect.py tests/test_launch_detect.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: add Forge/NeoForge launch detection"
```

---

### Task 4: ForgeInstaller

**Files:**
- Create: `src/server_studio/installers/forge.py`
- Test: `tests/test_forge_installer.py`

Resolves the Forge version from the promotions JSON, downloads the installer jar, runs
`java -jar <installer> --installServer` via the injected runner, then detects launch args.

- [ ] **Step 1: Write the failing test**

```python
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
        # simulate --installServer producing the modern args file
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_forge_installer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.installers.forge'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/installers/forge.py
from __future__ import annotations

from pathlib import Path

from server_studio.installers.base import InstallResult
from server_studio.installers.launch_detect import detect_launch_args
from server_studio.java_versions import java_major_for_version

PROMOTIONS = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
MAVEN = "https://maven.minecraftforge.net/net/minecraftforge/forge"


class ForgeInstaller:
    """Installs a Forge server by running the official installer jar."""

    def __init__(self, client, java_resolver, runner):
        self._client = client
        self._java_resolver = java_resolver
        self._runner = runner

    def _forge_version(self, mc_version: str) -> str:
        resp = self._client.get(PROMOTIONS)
        resp.raise_for_status()
        promos = resp.json().get("promos", {})
        version = promos.get(f"{mc_version}-recommended") or promos.get(f"{mc_version}-latest")
        if not version:
            raise ValueError(f"No Forge build for Minecraft {mc_version}")
        return version

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        forge_version = self._forge_version(mc_version)
        full = f"{mc_version}-{forge_version}"
        server_dir = dest.parent
        server_dir.mkdir(parents=True, exist_ok=True)

        installer_url = f"{MAVEN}/{full}/forge-{full}-installer.jar"
        resp = self._client.get(installer_url)
        resp.raise_for_status()
        installer_jar = server_dir / "forge-installer.jar"
        installer_jar.write_bytes(resp.content)

        java_major = java_major_for_version(mc_version)
        java = self._java_resolver(java_major)
        self._runner(
            [str(java), "-jar", installer_jar.name, "--installServer"],
            server_dir,
        )

        return InstallResult(
            jar_path=server_dir / "server.jar",
            java_major=java_major,
            launch_args=detect_launch_args(server_dir),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_forge_installer.py -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/installers/forge.py tests/test_forge_installer.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: add ForgeInstaller (run installer jar + detect launch)"
```

---

### Task 5: NeoForgeInstaller

**Files:**
- Create: `src/server_studio/installers/neoforge.py`
- Test: `tests/test_neoforge_installer.py`

NeoForge versions live in maven metadata (XML). The version for MC `1.20.6` is the highest
`20.6.*`; for `1.21` it's the highest `21.0.*` (NeoForge drops the leading "1." and uses
`minor.patch`). Then download + run the installer; detect launch (same helper — it produces
`libraries/net/neoforged/neoforge/<ver>/win_args.txt`).

- [ ] **Step 1: Write the failing test**

```python
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
        installer.install("1.19.2", tmp_path / "server.jar")  # no 19.2.* in metadata
        assert False, "expected ValueError"
    except ValueError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_neoforge_installer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.installers.neoforge'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/installers/neoforge.py
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from server_studio.installers.base import InstallResult
from server_studio.installers.launch_detect import detect_launch_args
from server_studio.java_versions import java_major_for_version

METADATA = "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml"
MAVEN = "https://maven.neoforged.net/releases/net/neoforged/neoforge"


def neoforge_prefix(mc_version: str) -> str:
    """MC 1.X.Y -> NeoForge version prefix 'X.Y' (patch defaults to 0)."""
    parts = mc_version.split(".")
    minor = parts[1]
    patch = parts[2] if len(parts) > 2 else "0"
    return f"{minor}.{patch}"


class NeoForgeInstaller:
    """Installs a NeoForge server by running the official installer jar."""

    def __init__(self, client, java_resolver, runner):
        self._client = client
        self._java_resolver = java_resolver
        self._runner = runner

    def _neoforge_version(self, mc_version: str) -> str:
        resp = self._client.get(METADATA)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        versions = [e.text for e in root.iter("version") if e.text]
        prefix = neoforge_prefix(mc_version) + "."
        matching = [v for v in versions if v.startswith(prefix)]
        if not matching:
            raise ValueError(f"No NeoForge build for Minecraft {mc_version}")
        # highest by the trailing integer build number
        return max(matching, key=lambda v: int(v.rsplit(".", 1)[-1]))

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        version = self._neoforge_version(mc_version)
        server_dir = dest.parent
        server_dir.mkdir(parents=True, exist_ok=True)

        installer_url = f"{MAVEN}/{version}/neoforge-{version}-installer.jar"
        resp = self._client.get(installer_url)
        resp.raise_for_status()
        installer_jar = server_dir / "neoforge-installer.jar"
        installer_jar.write_bytes(resp.content)

        java_major = java_major_for_version(mc_version)
        java = self._java_resolver(java_major)
        self._runner(
            [str(java), "-jar", installer_jar.name, "--installServer"],
            server_dir,
        )

        return InstallResult(
            jar_path=server_dir / "server.jar",
            java_major=java_major,
            launch_args=detect_launch_args(server_dir),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_neoforge_installer.py -v`
Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/installers/neoforge.py tests/test_neoforge_installer.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: add NeoForgeInstaller via maven metadata"
```

---

### Task 6: SpigotInstaller (BuildTools)

**Files:**
- Create: `src/server_studio/installers/spigot.py`
- Test: `tests/test_spigot_installer.py`

Downloads BuildTools.jar, runs `java -jar BuildTools.jar --rev <version>` in a work dir
(this compiles `spigot-<version>.jar`), then copies the built jar to the server's
`server.jar`. Launches with the default `-jar server.jar nogui`.

- [ ] **Step 1: Write the failing test**

```python
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
        (cwd / "spigot-1.20.6.jar").write_bytes(b"SPIGOTJAR")  # BuildTools output

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
                                runner=lambda c, d: None)  # produces nothing
    server_dir = tmp_path / "srv"; server_dir.mkdir()
    try:
        installer.install("1.20.6", server_dir / "server.jar")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_spigot_installer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.installers.spigot'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/installers/spigot.py
from __future__ import annotations

from pathlib import Path

from server_studio.installers.base import InstallResult
from server_studio.java_versions import java_major_for_version

BUILDTOOLS = (
    "https://hub.spigotmc.org/jenkins/job/BuildTools/"
    "lastSuccessfulBuild/artifact/target/BuildTools.jar"
)


class SpigotInstaller:
    """Builds a Spigot server jar via BuildTools."""

    def __init__(self, client, java_resolver, runner):
        self._client = client
        self._java_resolver = java_resolver
        self._runner = runner

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        server_dir = dest.parent
        work = server_dir / "buildtools"
        work.mkdir(parents=True, exist_ok=True)

        resp = self._client.get(BUILDTOOLS)
        resp.raise_for_status()
        (work / "BuildTools.jar").write_bytes(resp.content)

        java_major = java_major_for_version(mc_version)
        java = self._java_resolver(java_major)
        self._runner(
            [str(java), "-jar", "BuildTools.jar", "--rev", mc_version],
            work,
        )

        built = work / f"spigot-{mc_version}.jar"
        if not built.is_file():
            matches = sorted(work.glob("spigot-*.jar"))
            if not matches:
                raise RuntimeError("BuildTools did not produce a Spigot jar")
            built = matches[0]

        dest.write_bytes(built.read_bytes())
        return InstallResult(jar_path=dest, java_major=java_major)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_spigot_installer.py -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/installers/spigot.py tests/test_spigot_installer.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: add SpigotInstaller via BuildTools"
```

---

### Task 7: Registry — process installers need java + runner

**Files:**
- Modify: `src/server_studio/installers/registry.py`
- Test: `tests/test_installer_registry.py`

Extend the registry so process-based loaders receive a `java_resolver` and `runner`. Simple
loaders keep taking just `client`.

- [ ] **Step 1: Update the test**

Replace `tests/test_installer_registry.py` with:

```python
# tests/test_installer_registry.py
import pytest
from server_studio.installers.registry import build_installer, SUPPORTED_LOADERS
from server_studio.installers.vanilla import VanillaInstaller
from server_studio.installers.paper import PaperInstaller
from server_studio.installers.purpur import PurpurInstaller
from server_studio.installers.fabric import FabricInstaller
from server_studio.installers.forge import ForgeInstaller
from server_studio.installers.neoforge import NeoForgeInstaller
from server_studio.installers.spigot import SpigotInstaller

_J = lambda major: "/java"
_R = lambda command, cwd: None


@pytest.mark.parametrize("loader,cls", [
    ("vanilla", VanillaInstaller),
    ("paper", PaperInstaller),
    ("purpur", PurpurInstaller),
    ("fabric", FabricInstaller),
    ("forge", ForgeInstaller),
    ("neoforge", NeoForgeInstaller),
    ("spigot", SpigotInstaller),
])
def test_build_installer_returns_correct_type(loader, cls):
    inst = build_installer(loader, client=object(), java_resolver=_J, runner=_R)
    assert isinstance(inst, cls)


def test_simple_loader_without_java_or_runner_still_builds():
    assert isinstance(build_installer("paper", client=object()), PaperInstaller)


def test_process_loader_requires_java_and_runner():
    with pytest.raises(ValueError):
        build_installer("forge", client=object())


def test_unknown_loader_raises():
    with pytest.raises(ValueError):
        build_installer("bogus", client=object(), java_resolver=_J, runner=_R)


def test_supported_loaders_listed():
    assert set(SUPPORTED_LOADERS) == {
        "vanilla", "paper", "purpur", "fabric", "forge", "neoforge", "spigot",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_installer_registry.py -v`
Expected: FAIL — forge/neoforge/spigot not in registry; signature mismatch.

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/installers/registry.py
from __future__ import annotations

from server_studio.installers.base import Installer
from server_studio.installers.vanilla import VanillaInstaller
from server_studio.installers.paper import PaperInstaller
from server_studio.installers.purpur import PurpurInstaller
from server_studio.installers.fabric import FabricInstaller
from server_studio.installers.forge import ForgeInstaller
from server_studio.installers.neoforge import NeoForgeInstaller
from server_studio.installers.spigot import SpigotInstaller

_SIMPLE = {
    "vanilla": VanillaInstaller,
    "paper": PaperInstaller,
    "purpur": PurpurInstaller,
    "fabric": FabricInstaller,
}
_PROCESS = {
    "forge": ForgeInstaller,
    "neoforge": NeoForgeInstaller,
    "spigot": SpigotInstaller,
}

SUPPORTED_LOADERS = tuple(_SIMPLE) + tuple(_PROCESS)


def build_installer(loader: str, client, java_resolver=None, runner=None) -> Installer:
    """Construct the installer for `loader`, sharing the given HTTP client.

    Process-based loaders (forge/neoforge/spigot) also require `java_resolver` and
    `runner` because they run a Java process to install.
    """
    key = loader.lower()
    if key in _SIMPLE:
        return _SIMPLE[key](client=client)
    if key in _PROCESS:
        if java_resolver is None or runner is None:
            raise ValueError(f"Loader {loader!r} requires java_resolver and runner")
        return _PROCESS[key](client=client, java_resolver=java_resolver, runner=runner)
    raise ValueError(
        f"Unsupported loader: {loader!r}. Supported: {', '.join(SUPPORTED_LOADERS)}"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_installer_registry.py -v`
Expected: PASS (all cases).

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/installers/registry.py tests/test_installer_registry.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: register forge/neoforge/spigot installers"
```

---

### Task 8: Wire app + UI loader options

**Files:**
- Modify: `src/server_studio/app.py`
- Modify: `src/server_studio/ui/loader_options.py`
- Test: `tests/test_loader_options.py`

> **Sequencing note:** the UI animation pass runs concurrently in `src/server_studio/ui/`.
> Run this task only after that work has merged, to avoid touching `ui/loader_options.py`
> at the same time.

`app.py` passes the JavaManager resolver + the real runner to `build_installer`.
`loader_options.py` gains metadata for the three new loaders.

- [ ] **Step 1: Update the test**

In `tests/test_loader_options.py`, update the kind assertions test to include the new loaders:

```python
def test_options_have_label_and_kind():
    opts = loader_options_for_version("1.20.6")
    by_key = {o.key: o for o in opts}
    assert by_key["vanilla"].kind == "none"
    assert by_key["paper"].kind == "plugins"
    assert by_key["fabric"].kind == "mods"
    assert by_key["forge"].kind == "mods"
    assert by_key["neoforge"].kind == "mods"
    assert by_key["spigot"].kind == "plugins"
    for o in opts:
        assert o.label
```

(The existing `test_returns_one_option_per_supported_loader` already checks the set matches
`SUPPORTED_LOADERS`, so it will now expect all seven automatically.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_loader_options.py -v`
Expected: FAIL — `KeyError: 'forge'` (no metadata yet).

- [ ] **Step 3: Write minimal implementation**

In `src/server_studio/ui/loader_options.py`, extend `_META`:

```python
_META = {
    "vanilla": ("Vanilla", "none", "Pure Minecraft, no mods or plugins."),
    "paper": ("Paper", "plugins", "Fast, optimized. Best for plugin servers."),
    "purpur": ("Purpur", "plugins", "Paper plus extra customization options."),
    "fabric": ("Fabric", "mods", "Lightweight modding. Great for performance mods."),
    "forge": ("Forge", "mods", "The classic big-modpack platform."),
    "neoforge": ("NeoForge", "mods", "Modern Forge fork, growing fast."),
    "spigot": ("Spigot", "plugins", "Bukkit-based plugins (compiled via BuildTools)."),
}
```

In `src/server_studio/app.py`, update the wiring so the installer factory passes the Java
resolver and runner:

```python
# src/server_studio/app.py
from __future__ import annotations

import httpx

from server_studio.paths import AppPaths
from server_studio.manager import ServerManager
from server_studio.java_manager import JavaManager
from server_studio.process import ServerProcess
from server_studio.installers.registry import build_installer
from server_studio.installers.runner import run_process
from server_studio.temurin import temurin_fetcher


def build_server_manager(paths: AppPaths) -> ServerManager:
    """Construct a fully-wired ServerManager with real network + process backends."""
    paths.ensure()
    client = httpx.Client(follow_redirects=True, timeout=60.0)
    java = JavaManager(paths=paths, fetcher=temurin_fetcher(client))

    return ServerManager(
        paths=paths,
        installer_for=lambda loader: build_installer(
            loader, client=client, java_resolver=java.resolver, runner=run_process,
        ),
        process_factory=ServerProcess,
        java_resolver=java.resolver,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_loader_options.py -v` then `python -c "import server_studio.app"`
Expected: PASS; app imports cleanly.

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/app.py src/server_studio/ui/loader_options.py tests/test_loader_options.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: wire forge/neoforge/spigot into app + wizard options"
```

---

### Task 9: Full suite + README + manual QA

**Files:**
- Modify: `README.md`
- Modify: `docs/manual-qa-ui.md`
- Test: (whole suite)

- [ ] **Step 1: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS — all prior + new tests green.

- [ ] **Step 2: Update README status**

In `README.md`, update the `## Status` loader list to include Forge, NeoForge, and Spigot.

- [ ] **Step 3: Add real-world QA checks to `docs/manual-qa-ui.md`**

Append:

```markdown
## Loaders (Plan 2b — needs real network + Java)
- [ ] Create a **Forge** 1.20.x server: installer downloads, runs, and the server boots
      (launches via the @args file, not -jar).
- [ ] Create a **NeoForge** 1.21.x server: installer resolves the right version and boots.
- [ ] Create a **Spigot** server: BuildTools compiles (slow — minutes) and the jar boots.
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/manual-qa-ui.md
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "docs: Forge/NeoForge/Spigot status + QA checks"
```

---

## Self-Review Notes

- **Spec coverage:** delivers the deferred Forge/NeoForge/Spigot loaders from the Plan 2
  spec; generalizes launch so Forge/NeoForge boot via `@args.txt` (Task 1, 3) while the
  others keep `-jar server.jar nogui`.
- **Interface consistency:** all installers still satisfy `install(mc_version, dest) ->
  InstallResult`; process installers take `(client, java_resolver, runner)`; the registry
  routes deps; `app.py` injects `java.resolver` + `run_process`. `launch_args` flows
  InstallResult → ServerConfig → `start_server`.
- **Offline tests:** every network call and Java process is injected (fake client + fake
  runner); no unit test hits the network or runs Java. Real endpoints/process behavior are
  validated in Task 9 manual QA — flagged honestly, not asserted by unit tests.
- **Sequencing:** Task 8 touches `ui/loader_options.py`; run it after the concurrent UI
  animation pass merges.
