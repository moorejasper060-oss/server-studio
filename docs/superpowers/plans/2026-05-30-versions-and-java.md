# Server Studio — Plan 2: Versions & Java Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the API-based server loaders (Paper, Purpur, Fabric) and a JavaManager that auto-downloads the correct Temurin runtime, then wire them into `ServerManager` so creating a server of any of these loaders Just Works with the right Java.

**Architecture:** A shared `Installer` protocol + `InstallResult` in `installers/base.py`. One installer per loader (`vanilla` already exists; add `paper`, `purpur`, `fabric`), each taking an injected duck-typed HTTP client so tests run offline. A pure `java_major_for_version()` function maps MC version → required Java. `JavaManager` resolves a Java executable from a shared cache, downloading+extracting Temurin via an injected fetcher when missing. A `build_installer(loader, client)` registry maps loader names to installers. `ServerManager` is refactored to take an `installer_for(loader)` factory and a real `java_resolver` (JavaManager), and gains an "already running" guard.

**Tech Stack:** Python 3.12+, `httpx` (real client at the edges, faked in tests), `pytest`. Real public APIs: PaperMC v2, PurpurMC v2, Fabric Meta v2, Adoptium v3.

**Carry-forward from Plan 1:** add the `start_server` already-running guard (final-review finding) — done in Task 8.

**Deferred to Plan 2b:** Forge, NeoForge, Spigot (installer-process based).

---

### Task 1: Version → Java major mapping

**Files:**
- Create: `src/server_studio/java_versions.py`
- Test: `tests/test_java_versions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_java_versions.py
import pytest
from server_studio.java_versions import java_major_for_version


@pytest.mark.parametrize("version,expected", [
    ("1.8.9", 8),
    ("1.12.2", 8),
    ("1.16.5", 8),
    ("1.17", 17),
    ("1.17.1", 17),
    ("1.18.2", 17),
    ("1.19.4", 17),
    ("1.20", 17),
    ("1.20.4", 17),
    ("1.20.5", 21),
    ("1.20.6", 21),
    ("1.21", 21),
    ("1.21.4", 21),
])
def test_known_versions_map_to_expected_java(version, expected):
    assert java_major_for_version(version) == expected


def test_unparseable_version_defaults_to_21():
    assert java_major_for_version("garbage") == 21
    assert java_major_for_version("24w14a") == 21  # snapshot → default latest
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_java_versions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.java_versions'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/java_versions.py
from __future__ import annotations

DEFAULT_JAVA_MAJOR = 21


def java_major_for_version(mc_version: str) -> int:
    """Map a Minecraft *release* version (e.g. "1.20.6") to the required Java major.

    Rules (Mojang's): <=1.16 → 8, 1.17–1.20.4 → 17, >=1.20.5 → 21.
    Unparseable or snapshot strings fall back to the latest (21).
    """
    parts = mc_version.split(".")
    try:
        if parts[0] != "1":
            return DEFAULT_JAVA_MAJOR
        minor = int(parts[1])
        patch = int(parts[2]) if len(parts) > 2 else 0
    except (IndexError, ValueError):
        return DEFAULT_JAVA_MAJOR

    if minor <= 16:
        return 8
    if minor <= 19:
        return 17
    if minor == 20:
        return 17 if patch < 5 else 21
    return 21
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_java_versions.py -v`
Expected: PASS (all parametrized cases + default)

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/java_versions.py tests/test_java_versions.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: add version-to-Java major mapping

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Shared installer base (InstallResult + Installer protocol)

**Files:**
- Create: `src/server_studio/installers/base.py`
- Modify: `src/server_studio/installers/vanilla.py` (import `InstallResult` from base instead of defining it)
- Test: `tests/test_installer_base.py`

This extracts the shared result type so every loader installer returns the same shape, and
defines a `Protocol` documenting the installer interface. Vanilla keeps working unchanged
for callers.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_installer_base.py
from pathlib import Path
from server_studio.installers.base import InstallResult, Installer
from server_studio.installers.vanilla import VanillaInstaller


def test_install_result_fields():
    r = InstallResult(jar_path=Path("x/server.jar"), java_major=17)
    assert r.jar_path == Path("x/server.jar")
    assert r.java_major == 17


def test_vanilla_installer_satisfies_protocol():
    # VanillaInstaller is constructed with a client; we only check structural typing here.
    assert hasattr(VanillaInstaller, "install")
    # Protocol is runtime_checkable so isinstance works on instances.
    inst = VanillaInstaller(client=object())
    assert isinstance(inst, Installer)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_installer_base.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.installers.base'`

- [ ] **Step 3: Write minimal implementation**

Create `base.py`:

```python
# src/server_studio/installers/base.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class InstallResult:
    jar_path: Path
    java_major: int


@runtime_checkable
class Installer(Protocol):
    """A loader installer: download the runnable server jar to `dest`."""

    def install(self, mc_version: str, dest: Path) -> InstallResult: ...
```

Modify `vanilla.py` — replace its local `InstallResult` definition with an import. The new
top of `vanilla.py` becomes:

```python
# src/server_studio/installers/vanilla.py
from __future__ import annotations

from pathlib import Path

from server_studio.installers.base import InstallResult

MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"


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

(The only change vs Plan 1 is removing the local `@dataclass InstallResult` and the
`from dataclasses import dataclass` import, replacing with the base import.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_installer_base.py tests/test_vanilla_installer.py -v`
Expected: PASS — base tests pass AND the existing vanilla tests still pass (no regression).

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/installers/base.py src/server_studio/installers/vanilla.py tests/test_installer_base.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "refactor: extract shared InstallResult + Installer protocol

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: PaperInstaller (PaperMC v2 API)

**Files:**
- Create: `src/server_studio/installers/paper.py`
- Test: `tests/test_paper_installer.py`

PaperMC API flow: list builds for a version → take the highest build → read its download
filename → download that jar. Java major comes from `java_major_for_version` (Paper's API
doesn't report it). Uses the same duck-typed `client` as Vanilla.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_paper_installer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.installers.paper'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/installers/paper.py
from __future__ import annotations

from pathlib import Path

from server_studio.installers.base import InstallResult
from server_studio.java_versions import java_major_for_version

BASE = "https://api.papermc.io/v2/projects/paper/versions"


class PaperInstaller:
    """Resolves the latest Paper build for a version via the PaperMC v2 API."""

    def __init__(self, client):
        self._client = client

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        builds_resp = self._client.get(f"{BASE}/{mc_version}")
        builds_resp.raise_for_status()
        builds = builds_resp.json().get("builds", [])
        if not builds:
            raise ValueError(f"No Paper builds for Minecraft {mc_version}")
        build = max(builds)

        build_resp = self._client.get(f"{BASE}/{mc_version}/builds/{build}")
        build_resp.raise_for_status()
        jar_name = build_resp.json()["downloads"]["application"]["name"]

        download_url = f"{BASE}/{mc_version}/builds/{build}/downloads/{jar_name}"
        jar = self._client.get(download_url)
        jar.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(jar.content)
        return InstallResult(jar_path=dest, java_major=java_major_for_version(mc_version))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_paper_installer.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/installers/paper.py tests/test_paper_installer.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: add PaperInstaller via PaperMC v2 API

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: PurpurInstaller (PurpurMC v2 API)

**Files:**
- Create: `src/server_studio/installers/purpur.py`
- Test: `tests/test_purpur_installer.py`

Purpur flow: `GET /v2/purpur/{version}` returns `{"builds": {"latest": "2150", ...}}`;
download from `/v2/purpur/{version}/{build}/download`.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_purpur_installer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.installers.purpur'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/installers/purpur.py
from __future__ import annotations

from pathlib import Path

from server_studio.installers.base import InstallResult
from server_studio.java_versions import java_major_for_version

BASE = "https://api.purpurmc.org/v2/purpur"


class PurpurInstaller:
    """Resolves the latest Purpur build for a version via the PurpurMC v2 API."""

    def __init__(self, client):
        self._client = client

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        meta = self._client.get(f"{BASE}/{mc_version}")
        meta.raise_for_status()
        latest = meta.json().get("builds", {}).get("latest")
        if not latest:
            raise ValueError(f"No Purpur builds for Minecraft {mc_version}")

        jar = self._client.get(f"{BASE}/{mc_version}/{latest}/download")
        jar.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(jar.content)
        return InstallResult(jar_path=dest, java_major=java_major_for_version(mc_version))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_purpur_installer.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/installers/purpur.py tests/test_purpur_installer.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: add PurpurInstaller via PurpurMC v2 API

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: FabricInstaller (Fabric Meta v2)

**Files:**
- Create: `src/server_studio/installers/fabric.py`
- Test: `tests/test_fabric_installer.py`

Fabric flow: pick the latest stable loader for the game version
(`/v2/versions/loader/{game}`), pick the latest stable installer
(`/v2/versions/installer`), then download the prebuilt server launcher jar from
`/v2/versions/loader/{game}/{loader}/{installer}/server/jar`. That launcher runs exactly
like `java -jar server.jar nogui`, so no extra launch handling is needed.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fabric_installer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.installers.fabric'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/installers/fabric.py
from __future__ import annotations

from pathlib import Path

from server_studio.installers.base import InstallResult
from server_studio.java_versions import java_major_for_version

META = "https://meta.fabricmc.net/v2/versions"


class FabricInstaller:
    """Resolves a Fabric server launcher jar via the Fabric Meta v2 API."""

    def __init__(self, client):
        self._client = client

    def _latest_stable_loader(self, game: str) -> str:
        resp = self._client.get(f"{META}/loader/{game}")
        resp.raise_for_status()
        entries = resp.json()
        for entry in entries:
            loader = entry.get("loader", {})
            if loader.get("stable"):
                return loader["version"]
        if entries:
            return entries[0]["loader"]["version"]
        raise ValueError(f"No Fabric loader for Minecraft {game}")

    def _latest_stable_installer(self) -> str:
        resp = self._client.get(f"{META}/installer")
        resp.raise_for_status()
        entries = resp.json()
        for entry in entries:
            if entry.get("stable"):
                return entry["version"]
        if entries:
            return entries[0]["version"]
        raise ValueError("No Fabric installer available")

    def install(self, mc_version: str, dest: Path) -> InstallResult:
        loader = self._latest_stable_loader(mc_version)
        installer = self._latest_stable_installer()
        jar_url = f"{META}/loader/{mc_version}/{loader}/{installer}/server/jar"
        jar = self._client.get(jar_url)
        jar.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(jar.content)
        return InstallResult(jar_path=dest, java_major=java_major_for_version(mc_version))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fabric_installer.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/installers/fabric.py tests/test_fabric_installer.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: add FabricInstaller via Fabric Meta v2 API

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Installer registry

**Files:**
- Create: `src/server_studio/installers/registry.py`
- Test: `tests/test_installer_registry.py`

A single place mapping a loader name to a constructed installer (given a shared client).
Unknown loaders raise a clear error. This is what `ServerManager` will use.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_installer_registry.py
import pytest
from server_studio.installers.registry import build_installer, SUPPORTED_LOADERS
from server_studio.installers.vanilla import VanillaInstaller
from server_studio.installers.paper import PaperInstaller
from server_studio.installers.purpur import PurpurInstaller
from server_studio.installers.fabric import FabricInstaller


@pytest.mark.parametrize("loader,cls", [
    ("vanilla", VanillaInstaller),
    ("paper", PaperInstaller),
    ("purpur", PurpurInstaller),
    ("fabric", FabricInstaller),
])
def test_build_installer_returns_correct_type(loader, cls):
    inst = build_installer(loader, client=object())
    assert isinstance(inst, cls)


def test_loader_name_is_case_insensitive():
    assert isinstance(build_installer("PAPER", client=object()), PaperInstaller)


def test_unknown_loader_raises():
    with pytest.raises(ValueError):
        build_installer("forge", client=object())


def test_supported_loaders_listed():
    assert set(SUPPORTED_LOADERS) == {"vanilla", "paper", "purpur", "fabric"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_installer_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.installers.registry'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/installers/registry.py
from __future__ import annotations

from server_studio.installers.base import Installer
from server_studio.installers.vanilla import VanillaInstaller
from server_studio.installers.paper import PaperInstaller
from server_studio.installers.purpur import PurpurInstaller
from server_studio.installers.fabric import FabricInstaller

_BUILDERS = {
    "vanilla": VanillaInstaller,
    "paper": PaperInstaller,
    "purpur": PurpurInstaller,
    "fabric": FabricInstaller,
}

SUPPORTED_LOADERS = tuple(_BUILDERS)


def build_installer(loader: str, client) -> Installer:
    """Construct the installer for `loader`, sharing the given HTTP client."""
    try:
        builder = _BUILDERS[loader.lower()]
    except KeyError:
        raise ValueError(
            f"Unsupported loader: {loader!r}. Supported: {', '.join(SUPPORTED_LOADERS)}"
        )
    return builder(client=client)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_installer_registry.py -v`
Expected: PASS (all cases)

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/installers/registry.py tests/test_installer_registry.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: add installer registry mapping loader names to installers

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: JavaManager (auto-download Temurin, cached)

**Files:**
- Create: `src/server_studio/java_manager.py`
- Test: `tests/test_java_manager.py`

`JavaManager` resolves the path to a `java` executable for a given major version. It looks
in the shared cache (`AppPaths.java / "temurin-{major}" / "bin" / java[.exe]`); if absent,
it asks an injected `fetcher(major, dest_dir)` to populate that runtime directory. The
fetcher (real Adoptium download + archive extraction) is injected so tests stay offline and
don't extract real archives. `JavaManager.resolver` exposes a `Callable[[int], Path]`
matching what `ServerManager` expects.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_java_manager.py
import sys
from pathlib import Path
import pytest
from server_studio.paths import AppPaths
from server_studio.java_manager import JavaManager


def _java_exe_name():
    return "java.exe" if sys.platform == "win32" else "java"


def test_resolve_returns_cached_runtime_without_fetching(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()
    # Pre-seed a cached runtime for Java 17.
    runtime = paths.java / "temurin-17" / "bin"
    runtime.mkdir(parents=True)
    exe = runtime / _java_exe_name()
    exe.write_text("", encoding="utf-8")

    fetch_calls = []

    def fetcher(major, dest_dir):
        fetch_calls.append((major, dest_dir))

    mgr = JavaManager(paths=paths, fetcher=fetcher)
    result = mgr.resolve(17)

    assert result == exe
    assert fetch_calls == []  # already cached → no download


def test_resolve_invokes_fetcher_when_missing(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()

    def fetcher(major, dest_dir):
        # Simulate a successful download+extract by creating the executable.
        bin_dir = Path(dest_dir) / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        (bin_dir / _java_exe_name()).write_text("", encoding="utf-8")

    mgr = JavaManager(paths=paths, fetcher=fetcher)
    result = mgr.resolve(21)

    assert result == paths.java / "temurin-21" / "bin" / _java_exe_name()
    assert result.is_file()


def test_resolve_raises_if_fetcher_does_not_produce_executable(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()

    def fetcher(major, dest_dir):
        pass  # produces nothing

    mgr = JavaManager(paths=paths, fetcher=fetcher)
    with pytest.raises(RuntimeError):
        mgr.resolve(21)


def test_resolver_is_callable_matching_signature(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()
    runtime = paths.java / "temurin-8" / "bin"
    runtime.mkdir(parents=True)
    (runtime / _java_exe_name()).write_text("", encoding="utf-8")

    mgr = JavaManager(paths=paths, fetcher=lambda m, d: None)
    resolver = mgr.resolver
    assert callable(resolver)
    assert resolver(8) == runtime / _java_exe_name()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_java_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.java_manager'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/java_manager.py
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from server_studio.paths import AppPaths


def _java_exe_name() -> str:
    return "java.exe" if sys.platform == "win32" else "java"


class JavaManager:
    """Resolves a cached Java executable, downloading Temurin on demand.

    `fetcher(major: int, dest_dir: Path)` must populate `dest_dir` with a Temurin
    runtime (so that `dest_dir / "bin" / java[.exe]` exists). It is injected so the
    network download + archive extraction can be tested separately and so this class
    stays offline-testable.
    """

    def __init__(self, paths: AppPaths, fetcher: Callable[[int, Path], None]):
        self._paths = paths
        self._fetcher = fetcher

    def _runtime_dir(self, major: int) -> Path:
        return self._paths.java / f"temurin-{major}"

    def _exe_path(self, major: int) -> Path:
        return self._runtime_dir(major) / "bin" / _java_exe_name()

    def resolve(self, major: int) -> Path:
        exe = self._exe_path(major)
        if exe.is_file():
            return exe

        dest_dir = self._runtime_dir(major)
        dest_dir.mkdir(parents=True, exist_ok=True)
        self._fetcher(major, dest_dir)

        if not exe.is_file():
            raise RuntimeError(
                f"Java {major} download did not produce an executable at {exe}"
            )
        return exe

    @property
    def resolver(self) -> Callable[[int], Path]:
        return self.resolve
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_java_manager.py -v`
Expected: PASS (all four tests)

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/java_manager.py tests/test_java_manager.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: add JavaManager with cached Temurin resolution

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Wire loaders + Java into ServerManager (+ already-running guard)

**Files:**
- Modify: `src/server_studio/manager.py`
- Modify: `tests/test_manager.py`
- Test: `tests/test_manager.py` (updated)

`ServerManager` currently takes a single `installer`. Refactor it to take
`installer_for: Callable[[str], Installer]` (loader → installer) so it can build the right
loader. Also add the carry-forward guard: `start_server` raises if the server is already
running. The Plan 1 manager tests are updated to pass an `installer_for` factory.

- [ ] **Step 1: Update the failing tests**

In `tests/test_manager.py`, change `_make_manager` to provide `installer_for` instead of
`installer`, and add a guard test. Replace the `ServerManager(...)` construction and add the
new test:

```python
    mgr = ServerManager(
        paths=paths,
        installer_for=lambda loader: FakeInstaller(),
        process_factory=factory,
        java_resolver=lambda major: Path(f"/java/{major}/bin/java"),
    )
    return mgr, created
```

Add this test to the file:

```python
def test_start_twice_raises(tmp_path):
    mgr, _ = _make_manager(tmp_path)
    cfg = mgr.create_server(name="SMP", mc_version="1.20.6", loader="vanilla")
    mgr.start_server(cfg.id, on_output=lambda _l: None)
    try:
        mgr.start_server(cfg.id, on_output=lambda _l: None)
        assert False, "expected RuntimeError on double start"
    except RuntimeError:
        pass
```

Also update `test_start_uses_java_and_ram_flags` to additionally assert the `-Xms` cap:

```python
    assert "-Xms1024M" in proc.command
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_manager.py -v`
Expected: FAIL — `TypeError` (unexpected keyword `installer_for`) and the new guard test
fails.

- [ ] **Step 3: Update the implementation**

In `src/server_studio/manager.py`, change the constructor and `create_server`, and add the
guard in `start_server`. The updated relevant parts:

```python
    def __init__(self, paths: AppPaths, installer_for: Callable[[str], "Installer"],
                 process_factory: Callable, java_resolver: Callable[[int], Path]):
        self.paths = paths
        self._installer_for = installer_for
        self._process_factory = process_factory
        self._java_resolver = java_resolver
        self._running: dict[str, object] = {}

    def create_server(self, name: str, mc_version: str, loader: str,
                      ram_mb: int = 2048, port: int = 25565) -> ServerConfig:
        server_id = uuid.uuid4().hex[:12]
        server_dir = self.paths.server_dir(server_id)
        server_dir.mkdir(parents=True, exist_ok=True)

        installer = self._installer_for(loader)
        result = installer.install(mc_version, server_dir / "server.jar")
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
```

Add the guard at the top of `start_server`:

```python
    def start_server(self, server_id: str, on_output: Callable[[str], None]) -> None:
        if self.is_running(server_id):
            raise RuntimeError(f"Server {server_id} is already running")
        cfg = self.get(server_id)
        # ... rest unchanged ...
```

Add the import for type-hinting `Installer` at the top of the file:

```python
from server_studio.installers.base import Installer
```

(Keep all other methods — `list_servers`, `get`, `_java_major`, `is_running`,
`stop_server` — exactly as in Plan 1.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_manager.py -v`
Expected: PASS — all manager tests (including `test_start_twice_raises` and the `-Xms`
assertion).

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/manager.py tests/test_manager.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: ServerManager builds loader-specific installer + already-running guard

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Adoptium fetcher + app factory (integration)

**Files:**
- Create: `src/server_studio/temurin.py`
- Create: `src/server_studio/app.py`
- Test: `tests/test_temurin.py`

`temurin.py` holds the real Adoptium download+extract fetcher (the only piece that touches
the network and the filesystem archive). `app.py` wires everything into a ready
`ServerManager` using a real `httpx.Client`, the installer registry, a `JavaManager` backed
by the Temurin fetcher, and a `ServerProcess` factory. The fetcher's *archive extraction* is
unit-tested with a locally-built zip (no network); the network call is left thin and
covered by the URL-resolution test with a fake client.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_temurin.py
import io
import zipfile
from pathlib import Path
from server_studio.temurin import extract_runtime, resolve_download_url


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

    def get(self, url, **kwargs):
        return self.routes[url]


def test_resolve_download_url_picks_binary_link():
    api_url = (
        "https://api.adoptium.net/v3/assets/latest/17/hotspot"
        "?architecture=x64&image_type=jdk&os=windows"
    )
    routes = {api_url: FakeResponse(json_data=[
        {"binary": {"package": {"link": "https://example/jdk17.zip"}}},
    ])}
    url = resolve_download_url(FakeClient(routes), major=17, os_name="windows")
    assert url == "https://example/jdk17.zip"


def test_extract_runtime_flattens_single_top_dir(tmp_path):
    # Adoptium archives contain a single top-level dir like "jdk-17.0.11+9";
    # extract_runtime should flatten it so bin/ ends up directly under dest_dir.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("jdk-17.0.11+9/bin/java.exe", "binary")
        zf.writestr("jdk-17.0.11+9/release", "info")
    archive_bytes = buf.getvalue()

    dest_dir = tmp_path / "temurin-17"
    extract_runtime(archive_bytes, dest_dir, suffix=".zip")

    assert (dest_dir / "bin" / "java.exe").is_file()
    assert (dest_dir / "release").is_file()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_temurin.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'server_studio.temurin'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/server_studio/temurin.py
from __future__ import annotations

import io
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ADOPTIUM = "https://api.adoptium.net/v3/assets/latest/{major}/hotspot"


def _os_name() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def resolve_download_url(client, major: int, os_name: str | None = None) -> str:
    os_name = os_name or _os_name()
    url = ADOPTIUM.format(major=major)
    resp = client.get(
        url,
        params={"architecture": "x64", "image_type": "jdk", "os": os_name},
    )
    resp.raise_for_status()
    assets = resp.json()
    if not assets:
        raise RuntimeError(f"No Temurin {major} build for os={os_name}")
    return assets[0]["binary"]["package"]["link"]


def extract_runtime(archive_bytes: bytes, dest_dir: Path, suffix: str) -> None:
    """Extract a Temurin archive into dest_dir, flattening the single top-level dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as staging_str:
        staging = Path(staging_str)
        if suffix == ".zip":
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
                zf.extractall(staging)
        else:  # .tar.gz
            with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tf:
                tf.extractall(staging)

        tops = [p for p in staging.iterdir()]
        root = tops[0] if len(tops) == 1 and tops[0].is_dir() else staging
        for item in root.iterdir():
            target = dest_dir / item.name
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                for sub in item.rglob("*"):
                    rel = sub.relative_to(item)
                    dest = target / rel
                    if sub.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                    else:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(sub.read_bytes())
            else:
                target.write_bytes(item.read_bytes())


def temurin_fetcher(client):
    """Return a fetcher(major, dest_dir) that downloads + extracts Temurin."""
    def fetch(major: int, dest_dir: Path) -> None:
        url = resolve_download_url(client, major)
        suffix = ".zip" if url.endswith(".zip") else ".tar.gz"
        resp = client.get(url)
        resp.raise_for_status()
        extract_runtime(resp.content, dest_dir, suffix=suffix)
    return fetch
```

```python
# src/server_studio/app.py
from __future__ import annotations

import httpx

from server_studio.paths import AppPaths
from server_studio.manager import ServerManager
from server_studio.java_manager import JavaManager
from server_studio.process import ServerProcess
from server_studio.installers.registry import build_installer
from server_studio.temurin import temurin_fetcher


def build_server_manager(paths: AppPaths) -> ServerManager:
    """Construct a fully-wired ServerManager with real network + process backends."""
    paths.ensure()
    client = httpx.Client(follow_redirects=True, timeout=60.0)
    java = JavaManager(paths=paths, fetcher=temurin_fetcher(client))

    return ServerManager(
        paths=paths,
        installer_for=lambda loader: build_installer(loader, client=client),
        process_factory=ServerProcess,
        java_resolver=java.resolver,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_temurin.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add src/server_studio/temurin.py src/server_studio/app.py tests/test_temurin.py
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "feat: add Temurin fetcher + app factory wiring real backends

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Full suite green + README update

**Files:**
- Modify: `README.md`
- Test: (whole suite)

- [ ] **Step 1: Run the full suite**

Run: `python -m pytest -v`
Expected: PASS — all Plan 1 + Plan 2 tests green.

- [ ] **Step 2: Update the README Status section**

Replace the `## Status` paragraph with:

```markdown
## Status
Core foundation + loaders & Java. The Python core can create, start, stop, and stream
servers for Vanilla, Paper, Purpur, and Fabric, auto-downloading the correct Temurin Java
runtime. Forge/NeoForge/Spigot, the mod browser, tunnel, backups, and the UI arrive in
later plans.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git -c user.name="Jasper" -c user.email="moorejasper060@gmail.com" commit -m "docs: update README for loaders + Java

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## What's NOT in this plan

- **Plan 2b — Installer-process loaders:** Forge, NeoForge, Spigot (run a Java installer jar
  headlessly; needs a working Java from JavaManager, produces loader-specific launch
  commands — `ServerManager.start_server` will need per-loader launch handling).
- **Plan 3 — Mod/Plugin Browser**, **Plan 4 — Tunnel**, **Plan 5 — Backups**,
  **Plan 6 — UI**, **Plan 7 — Packaging** (unchanged from Plan 1's roadmap).

## Self-Review Notes

- **Spec coverage:** Adds Paper, Purpur, Fabric loaders + auto-Java (Adoptium/Temurin) +
  version-aware Java mapping from the spec's VersionManager/JavaManager sections.
  Forge/NeoForge/Spigot explicitly deferred to Plan 2b with rationale.
- **Interface consistency:** All installers return `InstallResult(jar_path, java_major)` and
  match the `Installer` protocol (`install(mc_version, dest)`). `JavaManager.resolve`
  signature `(int) -> Path` matches `ServerManager`'s `java_resolver` contract from Plan 1.
  `process_factory=ServerProcess` matches `(command, cwd, on_output)` from Plan 1.
- **Plan 1 carry-forward:** the `start_server` already-running guard from the final review is
  implemented in Task 8.
- **Refactor note:** Task 2 moves `InstallResult` to `installers/base.py` (vanilla updated,
  tests still green); Task 8 changes `ServerManager`'s `installer` param to an
  `installer_for(loader)` factory and updates the Plan 1 manager tests accordingly.
- **Offline-testable:** every network/archive piece is injected or tested with locally-built
  fixtures (fake clients, in-memory zip). No test hits the network or extracts a real JDK.
