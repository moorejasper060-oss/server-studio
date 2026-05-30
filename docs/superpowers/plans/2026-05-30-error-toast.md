# Server Studio — Error-Toast (Notification) Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Surface failures (server-create, mod install/search, backup create/restore) as a transient, non-blocking toast so the user gets feedback instead of silence.

**Architecture:** A `Toast` overlay widget on `MainWindow` with `show_message(text)` (fade in, auto-hide, fade out). `MainWindow._notify(msg)` drives it. A single `notify` callable is threaded into `ServerDetail` → `ModsTab`/`BackupsTab` (default no-op, so existing tests stay green); those widgets pass an `on_error` into their async `task_runner` calls that routes to `notify`. `MainWindow._on_create_failed` also routes to the toast.

---

### Task 1: Toast widget

**Files:** Create `src/server_studio/ui/widgets/toast.py`; Test `tests/test_toast.py`

- [ ] **Step 1: failing test**
```python
# tests/test_toast.py
from server_studio.ui.widgets.toast import Toast


def test_show_message_sets_text_and_shows(qtbot):
    t = Toast(); qtbot.addWidget(t)
    t.show_message("Something failed", duration_ms=50)
    assert t.text() == "Something failed"
    assert t.isVisible()


def test_show_message_replaces_text(qtbot):
    t = Toast(); qtbot.addWidget(t)
    t.show_message("first", duration_ms=50)
    t.show_message("second", duration_ms=50)
    assert t.text() == "second"
```

- [ ] **Step 2: run, verify FAIL**

- [ ] **Step 3: implement**
```python
# src/server_studio/ui/widgets/toast.py
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation
from PySide6.QtWidgets import QLabel, QGraphicsOpacityEffect


class Toast(QLabel):
    """A transient, non-blocking notification banner."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMargin(12)
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(0.0)
        self.hide()

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(180)

    def show_message(self, text: str, duration_ms: int = 4000) -> None:
        self.setText(text)
        self.adjustSize()
        if self.parent() is not None:
            self._reposition()
        self.show()
        self.raise_()
        self._fade_to(1.0)
        self._hide_timer.start(duration_ms)

    def _fade_to(self, value: float) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._effect.opacity())
        self._anim.setEndValue(value)
        self._anim.start()

    def _fade_out(self) -> None:
        self._fade_to(0.0)
        QTimer.singleShot(220, self.hide)

    def _reposition(self) -> None:
        parent = self.parent()
        if parent is None:
            return
        pr = parent.rect()
        self.move((pr.width() - self.width()) // 2, pr.height() - self.height() - 24)
```

- [ ] **Step 4: run, verify PASS**; full suite green.
- [ ] **Step 5: commit** — `feat: add Toast notification widget`

---

### Task 2: route failures to the toast

**Files:** Modify `ui/main_window.py`, `ui/widgets/server_detail.py`, `ui/widgets/mods_tab.py`, `ui/widgets/backups_tab.py`; Tests `tests/test_mods_tab.py`, `tests/test_backups_tab.py`, `tests/test_main_window.py` (additions)

- **ModsTab** `__init__`: add `notify=None`; store `self._notify = notify or (lambda _m: None)`. In `_do_search` and `_install_result`, pass an `on_error` to `self._run` that calls `self._notify`:
  - search: `self._run(lambda: self._service.search(query), self._show_results, lambda m: self._notify(f"Search failed: {m}"))`
  - install: `self._run(lambda: self._service.install(result), lambda _r: self.refresh_installed(), lambda m: self._notify(f"Install failed: {m}"))`
  Add a test: a fake service that raises in `install`, a fake `notify` collector, a synchronous default runner → assert the notify got the message.
- **BackupsTab** `__init__`: add `notify=None`; store `self._notify`. In `_create`/`_restore` pass `on_error` routing to `self._notify(f"Backup failed: {m}")` / `f"Restore failed: {m}"`. Add a test with a raising fake service.
- **ServerDetail** `__init__`: add `notify=None`; pass `notify=notify` to `ModsTab(...)` and `BackupsTab(...)`. Existing tests default None → no-op.
- **MainWindow**:
  - In `__init__`, create `self.toast = Toast(central)` (the central widget), keep a reference; reposition it on show. Add `def _notify(self, message): self.toast.show_message(message)`.
  - In `_open_server`, pass `notify=self._notify` to `ServerDetail(...)`.
  - In `_on_create_failed(self, message)`, also call `self._notify(f"Couldn't create server: {message}")` (keep storing `self._last_create_error`).
  - Add a `resizeEvent` that repositions the toast (`self.toast._reposition()` if visible). 
  Add a test: calling `w._notify("hi")` makes `w.toast.text() == "hi"`.

- [ ] verify: full suite green; `python -c "import server_studio.ui.main"`; offscreen smoke that `_notify` shows the toast.
- [ ] commit — `feat: surface create/mod/backup failures via toast`

---

## Self-Review Notes
- `notify` defaults to a no-op everywhere, so all existing widget/detail/main_window tests stay green; production threads the real toast.
- Errors already propagate through `AsyncRunner.failed` / `run_sync`'s `on_error`; this plan just connects an `on_error` that calls `notify`.
- Toast is non-modal (won't block tests or the UI); fade + auto-hide via QTimer/QPropertyAnimation.
