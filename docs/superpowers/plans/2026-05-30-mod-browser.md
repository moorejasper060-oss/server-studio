# Server Studio — Plan 3: Mod / Plugin Browser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Let users search and install mods/plugins from Modrinth (version+loader filtered), import local `.jar`s, and enable/disable/remove installed content — surfaced in the server detail "Mods" tab.

**Architecture:** A `ModrinthClient` (injected HTTP client) searches + resolves downloads, filtered by the server's MC version + loader. A `ContentManager` owns a server's content directory (`mods/` for Fabric/Forge/NeoForge, `plugins/` for Paper/Purpur/Spigot) and records installs in `ServerConfig.installed_content`; install/enable/disable/remove/import all go through it. The UI `ModsTab` drives search + the installed list. CurseForge is an optional, API-key-gated client with the same shape. All network is injected → suite stays offline.

**Tech Stack:** Python, httpx (faked in tests), PySide6 + pytest-qt for the tab.

---

### Task 1: Content target (mods vs plugins dir)

**Files:** Create `src/server_studio/installers/content_target.py`; Test `tests/test_content_target.py`

- [ ] **Step 1: failing test**
```python
# tests/test_content_target.py
import pytest
from server_studio.installers.content_target import content_dir_name, supports_content


@pytest.mark.parametrize("loader,expected", [
    ("fabric", "mods"), ("forge", "mods"), ("neoforge", "mods"),
    ("paper", "plugins"), ("purpur", "plugins"), ("spigot", "plugins"),
])
def test_content_dir(loader, expected):
    assert content_dir_name(loader) == expected


def test_vanilla_has_no_content_dir():
    assert content_dir_name("vanilla") is None
    assert supports_content("vanilla") is False
    assert supports_content("fabric") is True
```

- [ ] **Step 2: run, verify FAIL** — `python -m pytest tests/test_content_target.py -v`

- [ ] **Step 3: implement**
```python
# src/server_studio/installers/content_target.py
from __future__ import annotations

_MODS = {"fabric", "forge", "neoforge"}
_PLUGINS = {"paper", "purpur", "spigot"}


def content_dir_name(loader: str) -> str | None:
    key = loader.lower()
    if key in _MODS:
        return "mods"
    if key in _PLUGINS:
        return "plugins"
    return None


def supports_content(loader: str) -> bool:
    return content_dir_name(loader) is not None
```

- [ ] **Step 4: run, verify PASS**; then full suite green.
- [ ] **Step 5: commit** — `feat: add content target (mods/plugins dir per loader)`

---

### Task 2: ModrinthClient (search + version resolution)

**Files:** Create `src/server_studio/installers/modrinth.py`; Test `tests/test_modrinth.py`

Modrinth API: search `https://api.modrinth.com/v2/search?query=&facets=[["versions:1.20.6"],["categories:fabric"]]`;
project versions `https://api.modrinth.com/v2/project/{id}/version?game_versions=["1.20.6"]&loaders=["fabric"]`.

- [ ] **Step 1: failing test**
```python
# tests/test_modrinth.py
import json
from server_studio.installers.modrinth import ModrinthClient, ModResult, ModFile


class FakeResponse:
    def __init__(self, *, json_data=None, content=b""):
        self._json = json_data
        self.content = content
    def json(self): return self._json
    def raise_for_status(self): return None


class FakeClient:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []
    def get(self, url, params=None):
        self.calls.append((url, params))
        # match on url; params encoded by caller for facets
        return self.routes[url]


def test_search_filters_by_version_and_loader():
    url = "https://api.modrinth.com/v2/search"
    routes = {url: FakeResponse(json_data={"hits": [
        {"project_id": "AABB", "slug": "sodium", "title": "Sodium",
         "description": "perf", "downloads": 1000000},
    ]})}
    client = FakeClient(routes)
    mc = ModrinthClient(client=client)
    results = mc.search("sodium", mc_version="1.20.6", loader="fabric")
    assert results[0] == ModResult(project_id="AABB", slug="sodium", title="Sodium",
                                   description="perf", downloads=1000000)
    # facets must include both the version and the loader
    _, params = client.calls[0]
    facets = json.loads(params["facets"])
    assert ["versions:1.20.6"] in facets
    assert ["categories:fabric"] in facets


def test_get_files_returns_compatible_downloads():
    pid = "AABB"
    url = f"https://api.modrinth.com/v2/project/{pid}/version"
    routes = {url: FakeResponse(json_data=[
        {"id": "v1", "files": [
            {"filename": "sodium-1.20.6.jar", "url": "https://cdn/sodium.jar", "primary": True},
        ], "dependencies": []},
    ])}
    mc = ModrinthClient(client=FakeClient(routes))
    files = mc.get_files(pid, mc_version="1.20.6", loader="fabric")
    assert files[0] == ModFile(version_id="v1", filename="sodium-1.20.6.jar",
                               url="https://cdn/sodium.jar")
```

- [ ] **Step 2: run, verify FAIL**

- [ ] **Step 3: implement**
```python
# src/server_studio/installers/modrinth.py
from __future__ import annotations

import json
from dataclasses import dataclass

API = "https://api.modrinth.com/v2"


@dataclass
class ModResult:
    project_id: str
    slug: str
    title: str
    description: str
    downloads: int


@dataclass
class ModFile:
    version_id: str
    filename: str
    url: str


class ModrinthClient:
    """Searches Modrinth filtered to a server's MC version + loader."""

    def __init__(self, client):
        self._client = client

    def search(self, query: str, mc_version: str, loader: str) -> list[ModResult]:
        facets = json.dumps([[f"versions:{mc_version}"], [f"categories:{loader}"]])
        resp = self._client.get(f"{API}/search", params={"query": query, "facets": facets})
        resp.raise_for_status()
        out = []
        for hit in resp.json().get("hits", []):
            out.append(ModResult(
                project_id=hit["project_id"], slug=hit["slug"], title=hit["title"],
                description=hit.get("description", ""), downloads=hit.get("downloads", 0),
            ))
        return out

    def get_files(self, project_id: str, mc_version: str, loader: str) -> list[ModFile]:
        params = {
            "game_versions": json.dumps([mc_version]),
            "loaders": json.dumps([loader]),
        }
        resp = self._client.get(f"{API}/project/{project_id}/version", params=params)
        resp.raise_for_status()
        out = []
        for version in resp.json():
            primary = next((f for f in version["files"] if f.get("primary")),
                           version["files"][0] if version["files"] else None)
            if primary:
                out.append(ModFile(version_id=version["id"],
                                   filename=primary["filename"], url=primary["url"]))
        return out
```

- [ ] **Step 4: run, verify PASS**; full suite green.
- [ ] **Step 5: commit** — `feat: add ModrinthClient (version+loader filtered search)`

---

### Task 3: ContentManager (install / list / toggle / remove / import)

**Files:** Create `src/server_studio/content_manager.py`; Test `tests/test_content_manager.py`

Operates on a server by id: loads its `ServerConfig`, resolves the content dir, and
mutates both the directory and `installed_content`. A `downloader(url) -> bytes` is injected
for installs so tests stay offline.

- [ ] **Step 1: failing test**
```python
# tests/test_content_manager.py
import pytest
from server_studio.paths import AppPaths
from server_studio.config import ServerConfig
from server_studio.content_manager import ContentManager


def _server(tmp_path, loader="fabric"):
    paths = AppPaths(root=tmp_path); paths.ensure()
    sdir = paths.server_dir("s1"); sdir.mkdir(parents=True)
    ServerConfig(id="s1", name="S", mc_version="1.20.6", loader=loader).save(sdir / "server.json")
    return paths


def test_install_writes_jar_and_records(tmp_path):
    paths = _server(tmp_path)
    cm = ContentManager(paths, downloader=lambda url: b"JAR")
    cm.install("s1", source="modrinth", project_id="AABB", version_id="v1",
               filename="sodium.jar", url="https://cdn/sodium.jar")
    jar = paths.server_dir("s1") / "mods" / "sodium.jar"
    assert jar.read_bytes() == b"JAR"
    items = cm.list_installed("s1")
    assert items[0]["filename"] == "sodium.jar"
    assert items[0]["enabled"] is True


def test_disable_and_enable(tmp_path):
    paths = _server(tmp_path)
    cm = ContentManager(paths, downloader=lambda url: b"JAR")
    cm.install("s1", source="modrinth", project_id="A", version_id="v1",
               filename="m.jar", url="u")
    cm.set_enabled("s1", "m.jar", False)
    mods = paths.server_dir("s1") / "mods"
    assert (mods / "m.jar.disabled").is_file() and not (mods / "m.jar").exists()
    assert cm.list_installed("s1")[0]["enabled"] is False
    cm.set_enabled("s1", "m.jar", True)
    assert (mods / "m.jar").is_file()


def test_remove(tmp_path):
    paths = _server(tmp_path)
    cm = ContentManager(paths, downloader=lambda url: b"JAR")
    cm.install("s1", source="modrinth", project_id="A", version_id="v1",
               filename="m.jar", url="u")
    cm.remove("s1", "m.jar")
    assert not (paths.server_dir("s1") / "mods" / "m.jar").exists()
    assert cm.list_installed("s1") == []


def test_import_local_jar(tmp_path):
    paths = _server(tmp_path)
    src = tmp_path / "local.jar"; src.write_bytes(b"LOCAL")
    cm = ContentManager(paths, downloader=lambda url: b"")
    cm.import_jar("s1", src)
    assert (paths.server_dir("s1") / "mods" / "local.jar").read_bytes() == b"LOCAL"
    assert cm.list_installed("s1")[0]["source"] == "manual"


def test_install_on_vanilla_raises(tmp_path):
    paths = _server(tmp_path, loader="vanilla")
    cm = ContentManager(paths, downloader=lambda url: b"JAR")
    with pytest.raises(ValueError):
        cm.install("s1", source="modrinth", project_id="A", version_id="v1",
                   filename="m.jar", url="u")
```

- [ ] **Step 2: run, verify FAIL**

- [ ] **Step 3: implement**
```python
# src/server_studio/content_manager.py
from __future__ import annotations

from pathlib import Path
from typing import Callable

from server_studio.config import ServerConfig
from server_studio.paths import AppPaths
from server_studio.installers.content_target import content_dir_name


class ContentManager:
    """Manages a server's installed mods/plugins (files + config records)."""

    def __init__(self, paths: AppPaths, downloader: Callable[[str], bytes]):
        self._paths = paths
        self._downloader = downloader

    def _cfg_path(self, server_id: str) -> Path:
        return self._paths.server_dir(server_id) / "server.json"

    def _load(self, server_id: str) -> ServerConfig:
        return ServerConfig.load(self._cfg_path(server_id))

    def _content_dir(self, cfg: ServerConfig) -> Path:
        name = content_dir_name(cfg.loader)
        if name is None:
            raise ValueError(f"{cfg.loader} servers do not support mods or plugins")
        d = self._paths.server_dir(cfg.id) / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def list_installed(self, server_id: str) -> list[dict]:
        return self._load(server_id).installed_content

    def install(self, server_id: str, *, source: str, project_id: str, version_id: str,
                filename: str, url: str) -> None:
        cfg = self._load(server_id)
        target = self._content_dir(cfg) / filename
        target.write_bytes(self._downloader(url))
        cfg.installed_content.append({
            "source": source, "project_id": project_id, "version_id": version_id,
            "filename": filename, "enabled": True,
        })
        cfg.save(self._cfg_path(server_id))

    def import_jar(self, server_id: str, src: Path) -> None:
        cfg = self._load(server_id)
        target = self._content_dir(cfg) / src.name
        target.write_bytes(src.read_bytes())
        cfg.installed_content.append({
            "source": "manual", "project_id": None, "version_id": None,
            "filename": src.name, "enabled": True,
        })
        cfg.save(self._cfg_path(server_id))

    def set_enabled(self, server_id: str, filename: str, enabled: bool) -> None:
        cfg = self._load(server_id)
        d = self._content_dir(cfg)
        active, disabled = d / filename, d / f"{filename}.disabled"
        if enabled and disabled.is_file():
            disabled.rename(active)
        elif not enabled and active.is_file():
            active.rename(disabled)
        for item in cfg.installed_content:
            if item["filename"] == filename:
                item["enabled"] = enabled
        cfg.save(self._cfg_path(server_id))

    def remove(self, server_id: str, filename: str) -> None:
        cfg = self._load(server_id)
        d = self._content_dir(cfg)
        for candidate in (d / filename, d / f"{filename}.disabled"):
            if candidate.is_file():
                candidate.unlink()
        cfg.installed_content = [i for i in cfg.installed_content if i["filename"] != filename]
        cfg.save(self._cfg_path(server_id))
```

- [ ] **Step 4: run, verify PASS**; full suite green.
- [ ] **Step 5: commit** — `feat: add ContentManager (install/toggle/remove/import mods)`

---

### Task 4: CurseForge client (optional, key-gated)

**Files:** Create `src/server_studio/installers/curseforge.py`; Test `tests/test_curseforge.py`

Same shape as Modrinth but requires an API key. `from_env()` builds it from
`CURSEFORGE_API_KEY` or returns `None` (disabled).

- [ ] **Step 1: failing test**
```python
# tests/test_curseforge.py
from server_studio.installers.curseforge import CurseForgeClient, ModResult


class FakeResponse:
    def __init__(self, json_data):
        self._json = json_data
    def json(self): return self._json
    def raise_for_status(self): return None


class FakeClient:
    def __init__(self, routes):
        self.routes = routes
        self.headers_seen = []
    def get(self, url, params=None, headers=None):
        self.headers_seen.append(headers)
        return self.routes[url]


def test_search_sends_api_key_and_filters():
    url = "https://api.curseforge.com/v1/mods/search"
    routes = {url: FakeResponse({"data": [
        {"id": 12345, "slug": "jei", "name": "JEI", "summary": "items",
         "downloadCount": 50000000},
    ]})}
    client = FakeClient(routes)
    cf = CurseForgeClient(client=client, api_key="KEY123")
    results = cf.search("jei", mc_version="1.20.6", loader="forge")
    assert results[0] == ModResult(project_id="12345", slug="jei", title="JEI",
                                   description="items", downloads=50000000)
    assert client.headers_seen[0]["x-api-key"] == "KEY123"


def test_from_env_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("CURSEFORGE_API_KEY", raising=False)
    assert CurseForgeClient.from_env(client=object()) is None


def test_from_env_builds_with_key(monkeypatch):
    monkeypatch.setenv("CURSEFORGE_API_KEY", "ABC")
    cf = CurseForgeClient.from_env(client=object())
    assert isinstance(cf, CurseForgeClient)
```

- [ ] **Step 2: run, verify FAIL**

- [ ] **Step 3: implement**
```python
# src/server_studio/installers/curseforge.py
from __future__ import annotations

import os
from dataclasses import dataclass

API = "https://api.curseforge.com/v1"
_LOADER_TYPE = {"forge": 1, "fabric": 4, "quilt": 5, "neoforge": 6}


@dataclass
class ModResult:
    project_id: str
    slug: str
    title: str
    description: str
    downloads: int


class CurseForgeClient:
    """Searches CurseForge (requires an API key)."""

    def __init__(self, client, api_key: str):
        self._client = client
        self._api_key = api_key

    @classmethod
    def from_env(cls, client) -> "CurseForgeClient | None":
        key = os.environ.get("CURSEFORGE_API_KEY")
        return cls(client=client, api_key=key) if key else None

    def search(self, query: str, mc_version: str, loader: str) -> list[ModResult]:
        params = {"gameId": 432, "searchFilter": query, "gameVersion": mc_version}
        loader_type = _LOADER_TYPE.get(loader.lower())
        if loader_type is not None:
            params["modLoaderType"] = loader_type
        resp = self._client.get(f"{API}/mods/search", params=params,
                                headers={"x-api-key": self._api_key})
        resp.raise_for_status()
        out = []
        for mod in resp.json().get("data", []):
            out.append(ModResult(
                project_id=str(mod["id"]), slug=mod["slug"], title=mod["name"],
                description=mod.get("summary", ""), downloads=mod.get("downloadCount", 0),
            ))
        return out
```

- [ ] **Step 4: run, verify PASS**; full suite green.
- [ ] **Step 5: commit** — `feat: add optional CurseForge client (API-key gated)`

---

### Task 5: Mods tab UI widget

**Files:** Create `src/server_studio/ui/widgets/mods_tab.py`; Test `tests/test_mods_tab.py`

A `ModsTab(QWidget)` with a search field + results list (Install buttons) and an installed
list (toggle/remove). It is driven by an injected `service` object exposing
`search(query)->list`, `install(result)`, `list_installed()->list`, `set_enabled(name,bool)`,
`remove(name)`. Decoupling via the service keeps the widget testable with a fake.

- [ ] **Step 1: failing test**
```python
# tests/test_mods_tab.py
from server_studio.ui.widgets.mods_tab import ModsTab


class FakeService:
    def __init__(self):
        self.installed = []
        self.results = [{"project_id": "A", "title": "Sodium", "description": "perf"}]
        self.actions = []
    def search(self, query):
        self.actions.append(("search", query))
        return self.results
    def install(self, result):
        self.actions.append(("install", result["project_id"]))
        self.installed.append({"filename": "sodium.jar", "enabled": True})
    def list_installed(self):
        return self.installed
    def set_enabled(self, filename, enabled):
        self.actions.append(("toggle", filename, enabled))
    def remove(self, filename):
        self.actions.append(("remove", filename))
        self.installed = [i for i in self.installed if i["filename"] != filename]


def test_search_populates_results(qtbot):
    svc = FakeService()
    w = ModsTab(service=svc); qtbot.addWidget(w)
    w.search_input.setText("sodium")
    w._do_search()
    assert w.results_list.count() == 1
    assert ("search", "sodium") in svc.actions


def test_install_calls_service_and_refreshes(qtbot):
    svc = FakeService()
    w = ModsTab(service=svc); qtbot.addWidget(w)
    w._do_search()
    w._install_result(svc.results[0])
    assert ("install", "A") in svc.actions
    assert w.installed_list.count() == 1


def test_refresh_lists_installed(qtbot):
    svc = FakeService()
    svc.installed = [{"filename": "x.jar", "enabled": True}]
    w = ModsTab(service=svc); qtbot.addWidget(w)
    w.refresh_installed()
    assert w.installed_list.count() == 1
```

- [ ] **Step 2: run, verify FAIL**

- [ ] **Step 3: implement**
```python
# src/server_studio/ui/widgets/mods_tab.py
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget,
    QListWidgetItem, QLabel,
)


class ModsTab(QWidget):
    """Search + install mods/plugins and manage installed content via an injected service."""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service
        self._results = []

        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search mods/plugins…")
        self.search_input.returnPressed.connect(self._do_search)
        self.search_btn = QPushButton("Search", self)
        self.search_btn.setObjectName("Accent")
        self.search_btn.clicked.connect(self._do_search)
        row.addWidget(self.search_input, 1)
        row.addWidget(self.search_btn)
        layout.addLayout(row)

        layout.addWidget(QLabel("Results", self))
        self.results_list = QListWidget(self)
        layout.addWidget(self.results_list, 1)

        layout.addWidget(QLabel("Installed", self))
        self.installed_list = QListWidget(self)
        layout.addWidget(self.installed_list, 1)

        self.refresh_installed()

    def _do_search(self) -> None:
        self._results = self._service.search(self.search_input.text().strip())
        self.results_list.clear()
        for r in self._results:
            item = QListWidgetItem(f"{r['title']} — {r.get('description', '')[:60]}")
            btn_row = QWidget()
            hl = QHBoxLayout(btn_row); hl.setContentsMargins(0, 0, 0, 0)
            label = QLabel(f"{r['title']}")
            install = QPushButton("Install"); install.setObjectName("AccentGhost")
            install.clicked.connect(lambda _=False, res=r: self._install_result(res))
            hl.addWidget(label, 1); hl.addWidget(install)
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, btn_row)

    def _install_result(self, result: dict) -> None:
        self._service.install(result)
        self.refresh_installed()

    def refresh_installed(self) -> None:
        self.installed_list.clear()
        for item in self._service.list_installed():
            row = QListWidgetItem()
            w = QWidget()
            hl = QHBoxLayout(w); hl.setContentsMargins(0, 0, 0, 0)
            name = QLabel(item["filename"])
            toggle = QPushButton("Disable" if item["enabled"] else "Enable")
            toggle.clicked.connect(
                lambda _=False, f=item["filename"], en=item["enabled"]: self._toggle(f, not en))
            remove = QPushButton("Remove")
            remove.clicked.connect(lambda _=False, f=item["filename"]: self._remove(f))
            hl.addWidget(name, 1); hl.addWidget(toggle); hl.addWidget(remove)
            self.installed_list.addItem(row)
            self.installed_list.setItemWidget(row, w)

    def _toggle(self, filename: str, enabled: bool) -> None:
        self._service.set_enabled(filename, enabled)
        self.refresh_installed()

    def _remove(self, filename: str) -> None:
        self._service.remove(filename)
        self.refresh_installed()
```

- [ ] **Step 4: run, verify PASS**; full suite green.
- [ ] **Step 5: commit** — `feat: add ModsTab widget`

---

### Task 6: Content service + wire ModsTab into ServerDetail & app

**Files:** Create `src/server_studio/ui/content_service.py`; Modify `src/server_studio/ui/widgets/server_detail.py`; Modify `src/server_studio/ui/main_window.py`; Modify `src/server_studio/app.py`; Tests `tests/test_content_service.py`, update `tests/test_server_detail.py`

`ContentService` adapts a server + ModrinthClient + ContentManager to the `ModsTab` service
interface. `ServerDetail` gains an optional `content_service` and shows a real `ModsTab` when
provided (placeholder otherwise). `MainWindow._open_server` builds the service; `app.py`
exposes the pieces.

- [ ] **Step 1: failing test**
```python
# tests/test_content_service.py
from server_studio.ui.content_service import ContentService


class FakeSearch:
    def search(self, query, mc_version, loader):
        return [type("R", (), {"project_id": "A", "title": "Sodium",
                               "description": "perf", "slug": "sodium"})()]
    def get_files(self, project_id, mc_version, loader):
        return [type("F", (), {"version_id": "v1", "filename": "sodium.jar",
                               "url": "https://cdn/s.jar"})()]


class FakeContent:
    def __init__(self):
        self.installed = []
    def install(self, server_id, *, source, project_id, version_id, filename, url):
        self.installed.append(filename)
    def list_installed(self, server_id):
        return [{"filename": f, "enabled": True} for f in self.installed]
    def set_enabled(self, server_id, filename, enabled): pass
    def remove(self, server_id, filename): pass


def test_service_search_and_install():
    svc = ContentService(server_id="s1", mc_version="1.20.6", loader="fabric",
                         search_client=FakeSearch(), content=FakeContent())
    results = svc.search("sodium")
    assert results[0]["title"] == "Sodium"
    svc.install(results[0])
    assert svc.list_installed()[0]["filename"] == "sodium.jar"
```

- [ ] **Step 2: run, verify FAIL**

- [ ] **Step 3: implement**
```python
# src/server_studio/ui/content_service.py
from __future__ import annotations


class ContentService:
    """Adapts a ModrinthClient + ContentManager to the ModsTab service interface."""

    def __init__(self, server_id, mc_version, loader, search_client, content):
        self._sid = server_id
        self._mc = mc_version
        self._loader = loader
        self._search = search_client
        self._content = content

    def search(self, query: str) -> list[dict]:
        results = self._search.search(query, self._mc, self._loader)
        return [{"project_id": r.project_id, "title": r.title,
                 "description": r.description, "slug": r.slug} for r in results]

    def install(self, result: dict) -> None:
        files = self._search.get_files(result["project_id"], self._mc, self._loader)
        if not files:
            raise ValueError(f"No compatible file for {result['title']}")
        f = files[0]
        self._content.install(self._sid, source="modrinth",
                              project_id=result["project_id"], version_id=f.version_id,
                              filename=f.filename, url=f.url)

    def list_installed(self) -> list[dict]:
        return self._content.list_installed(self._sid)

    def set_enabled(self, filename: str, enabled: bool) -> None:
        self._content.set_enabled(self._sid, filename, enabled)

    def remove(self, filename: str) -> None:
        self._content.remove(self._sid, filename)
```

Then in `server_detail.py`: add an optional `content_service=None` kwarg; if provided AND the
loader supports content, build a `ModsTab(service=content_service)` and use it as the "Mods"
tab instead of the placeholder. Keep the `tabs`/`console`/etc attributes. In
`main_window._open_server`, build a `ContentService` (using injected `search_client` +
`content_manager`) and pass it to `ServerDetail` when the loader supports content. In
`app.py`'s `build_server_manager`, also construct + expose a `ModrinthClient(client)` and a
`ContentManager(paths, downloader=<httpx get .content>)`; provide a small accessor the UI
entrypoint uses. (Implementer: keep `ServerDetail`'s existing tests green — the new kwarg is
optional and defaults to placeholder behavior.)

- [ ] **Step 4: run, verify PASS** (new + existing detail tests); full suite green.
- [ ] **Step 5: commit** — `feat: wire mods browser into server detail + app`

---

### Task 7: Full suite + README + QA

- [ ] Run `python -m pytest -q` — all green.
- [ ] README: note the mod/plugin browser (Modrinth + manual import; CurseForge optional via `CURSEFORGE_API_KEY`).
- [ ] Append to `docs/manual-qa-ui.md`: open a Fabric server's Mods tab, search "sodium", install, see it in mods/, disable/enable/remove.
- [ ] Commit — `docs: mod browser status + QA`

---

## Self-Review Notes
- Covers Modrinth search (version+loader filtered), install/toggle/remove/manual import, optional CurseForge, and the Mods-tab UI — the spec's mod-browser feature. Dependency auto-resolution is intentionally minimal (installs the primary file); deeper dependency trees are a future refinement.
- All network injected; suite stays offline. `ContentService`/`service` indirection keeps the widget testable.
- Interfaces: `ModResult/ModFile`, `ContentManager.install(server_id, *, source, project_id, version_id, filename, url)`, `ContentService` adapter, `ModsTab(service=...)` used consistently.
