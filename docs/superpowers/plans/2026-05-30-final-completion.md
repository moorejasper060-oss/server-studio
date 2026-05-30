# Server Studio — Final Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Close the remaining completeness gaps: a real (fetched) Minecraft version list in the New Server wizard, tooltips on the icon-rail glyphs, and a current packaged `.exe`.

---

### Task 1: Dynamic Minecraft version list + rail tooltips

**Files:** Create `src/server_studio/installers/version_list.py`; Modify `src/server_studio/app.py`, `src/server_studio/ui/main.py`, `src/server_studio/ui/main_window.py`; Tests `tests/test_version_list.py`

- [ ] **Step 1: failing test**
```python
# tests/test_version_list.py
from server_studio.installers.version_list import list_release_versions, DEFAULT_VERSIONS


class FakeResp:
    def __init__(self, j): self._j = j
    def json(self): return self._j
    def raise_for_status(self): return None


class FakeClient:
    def __init__(self, j): self._j = j
    def get(self, url): return FakeResp(self._j)


def test_filters_to_releases_newest_first():
    data = {"versions": [
        {"id": "1.20.6", "type": "release"},
        {"id": "24w14a", "type": "snapshot"},
        {"id": "1.20.4", "type": "release"},
    ]}
    assert list_release_versions(FakeClient(data)) == ["1.20.6", "1.20.4"]


def test_default_versions_nonempty():
    assert DEFAULT_VERSIONS and all(isinstance(v, str) for v in DEFAULT_VERSIONS)
```

- [ ] **Step 2: run, verify FAIL**

- [ ] **Step 3: implement** `version_list.py`:
```python
# src/server_studio/installers/version_list.py
from __future__ import annotations

MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
DEFAULT_VERSIONS = ["1.21.4", "1.20.6", "1.20.4", "1.16.5"]


def list_release_versions(client) -> list[str]:
    """Fetch Minecraft *release* version ids (newest first) from the Mojang manifest."""
    resp = client.get(MANIFEST_URL)
    resp.raise_for_status()
    data = resp.json()
    return [v["id"] for v in data.get("versions", []) if v.get("type") == "release"]
```

Then:
- `app.py`: add
```python
def build_version_list() -> list[str]:
    """Fetch the release version list once (fallback to a static list on failure)."""
    from server_studio.installers.version_list import list_release_versions, DEFAULT_VERSIONS
    try:
        with httpx.Client(timeout=5.0) as client:
            versions = list_release_versions(client)
        return versions or DEFAULT_VERSIONS
    except Exception:
        return DEFAULT_VERSIONS
```
- `main_window.py`: in `__init__`, add a `versions=None` kwarg; `from server_studio.installers.version_list import DEFAULT_VERSIONS`; set `self._versions = versions or DEFAULT_VERSIONS`. In `_start_new_server`, use `self._versions` directly (drop the `getattr` fallback). Also set tooltips on the rail buttons: `self.nav_dash.setToolTip("Dashboard")`, `self.nav_settings.setToolTip("Settings")` (and any new-server rail icon → "New server").
- `main.py`: `make_window` gains `versions=None` passed through to `MainWindow`; `main()` builds `versions = build_version_list()` and passes `versions=versions`.

Existing `main_window`/`main_entry` tests construct without `versions` → default. Keep green.

- [ ] **Step 4: verify** — `python -m pytest tests/test_version_list.py tests/test_main_window.py tests/test_main_entry.py -v`; full suite green; `python -c "import server_studio.ui.main"`.
- [ ] **Step 5: commit** — `feat: fetch real Minecraft version list + rail tooltips`

---

### Task 2: Rebuild the packaged .exe (release step)

- [ ] Run `python -m PyInstaller --noconfirm server-studio.spec`.
- [ ] Confirm `dist/ServerStudio/ServerStudio.exe` launches (process stays alive).
- [ ] No commit (dist/ is gitignored); this just refreshes the local deliverable.

---

## Self-Review Notes
- Version list fetched once at startup with a short timeout + static fallback, so a slow/offline network never blocks or breaks the wizard.
- Tooltips make the glyph-only rail discoverable.
- All network injected in tests; suite stays offline.
