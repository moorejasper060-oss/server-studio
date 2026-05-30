# Server Studio — UI Async-Responsiveness Polish Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Stop the UI freezing on slow user-initiated actions (mod search/install, backup create/restore) by running them off the UI thread — without breaking the existing synchronous widget tests.

**Architecture:** An injectable `task_runner(fn, on_done, on_error=None)`. The default `run_sync` runs `fn()` inline and calls `on_done(result)` (so existing tests stay synchronous and green). Production injects `AsyncRunner` which runs `fn` on a `QThread` and marshals `on_done`/`on_error` back to the UI thread via signals. `ModsTab` and `BackupsTab` route their heavy actions through the runner; `ServerDetail` threads a `task_runner` down to them; `MainWindow` passes the async runner in production.

---

### Task 1: async_runner (run_sync + AsyncRunner)

**Files:** Create `src/server_studio/ui/async_runner.py`; Test `tests/test_async_runner.py`

- [ ] **Step 1: failing test**
```python
# tests/test_async_runner.py
from server_studio.ui.async_runner import run_sync, AsyncRunner


def test_run_sync_calls_on_done_with_result():
    got = []
    run_sync(lambda: 42, got.append)
    assert got == [42]


def test_run_sync_calls_on_error():
    errs = []
    def boom(): raise RuntimeError("nope")
    run_sync(boom, lambda r: None, errs.append)
    assert "nope" in errs[0]


def test_run_sync_without_on_error_swallows():
    # no on_error provided -> error is swallowed, on_done not called
    done = []
    run_sync((lambda: (_ for _ in ()).throw(ValueError("x"))), done.append)
    assert done == []


def test_async_runner_runs_and_emits(qtbot):
    runner = AsyncRunner()
    got = []
    with qtbot.waitSignal(runner._signals.done, timeout=2000):
        runner(lambda: 7, got.append)
    qtbot.waitUntil(lambda: got == [7], timeout=2000)
```

- [ ] **Step 2: run, verify FAIL**

- [ ] **Step 3: implement**
```python
# src/server_studio/ui/async_runner.py
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal


def run_sync(fn: Callable, on_done: Callable, on_error: Callable[[str], None] | None = None) -> None:
    """Run fn() inline; call on_done(result) or on_error(msg). Used in tests."""
    try:
        result = fn()
    except Exception as exc:
        if on_error:
            on_error(str(exc))
        return
    on_done(result)


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)


class _Worker(QThread):
    def __init__(self, fn, signals):
        super().__init__()
        self._fn = fn
        self._signals = signals

    def run(self):
        try:
            result = self._fn()
        except Exception as exc:
            self._signals.failed.emit(str(exc))
            return
        self._signals.done.emit(result)


class AsyncRunner:
    """Runs fn() on a QThread; delivers on_done/on_error on the UI thread via signals."""

    def __init__(self):
        self._signals = _Signals()
        self._threads: list[_Worker] = []

    def __call__(self, fn, on_done, on_error=None) -> None:
        signals = _Signals()
        worker = _Worker(fn, signals)
        signals.done.connect(on_done)
        if on_error:
            signals.failed.connect(on_error)
        signals.done.connect(lambda *_: self._cleanup(worker))
        signals.failed.connect(lambda *_: self._cleanup(worker))
        worker._signals = signals
        self._signals = signals  # expose latest for tests
        self._threads.append(worker)
        worker.start()

    def _cleanup(self, worker) -> None:
        if worker in self._threads:
            self._threads.remove(worker)
```

- [ ] **Step 4: run, verify PASS**; full suite green.
- [ ] **Step 5: commit** — `feat: add task runner (sync default + async QThread)`

---

### Task 2: route ModsTab + BackupsTab heavy actions through the runner

**Files:** Modify `ui/widgets/mods_tab.py`, `ui/widgets/backups_tab.py`; update their tests if needed (they should still pass with the default `run_sync`).

- ModsTab: `__init__(self, service, task_runner=run_sync, parent=None)`. `_do_search` → `self._run(lambda: self._service.search(q), self._show_results)`. `_install_result` → `self._run(lambda: self._service.install(result), lambda _r: self.refresh())`. Keep `refresh_installed`/toggle/remove synchronous (cheap) OR route install only. Existing tests use default `run_sync` → results delivered inline → assertions hold.
- BackupsTab: `__init__(self, service, task_runner=run_sync, parent=None)`. `_create`/`_restore` routed through the runner; `refresh` after. Existing tests pass with `run_sync`.
- [ ] TDD: confirm existing mods/backups tab tests stay green; add a test that a provided fake runner is used.
- [ ] commit — `feat: run mod/backup actions through injectable task runner`

---

### Task 3: thread the async runner through ServerDetail + MainWindow

**Files:** Modify `ui/widgets/server_detail.py`, `ui/main_window.py`, `ui/main.py`.

- `ServerDetail.__init__`: add `task_runner=run_sync`; pass it to `ModsTab(...)` and `BackupsTab(...)`. Existing detail tests default to `run_sync` → green.
- `MainWindow.__init__`: add `task_runner=None`; in `_open_server`, pass `task_runner=self._task_runner or run_sync` to ServerDetail.
- `main.py`: build a single `AsyncRunner()` and pass `task_runner=` to `make_window`/`MainWindow`.
- [ ] verify: full suite green; offscreen smoke; `python -c "import server_studio.ui.main"`.
- [ ] commit — `feat: use async task runner for server-detail actions in the app`

---

## Self-Review Notes
- The injectable runner keeps all existing widget tests synchronous (default `run_sync`) while production gets off-thread execution → no UI freeze on slow search/install/backup.
- `on_done`/`on_error` are delivered on the UI thread via Qt signals (queued cross-thread), so slot code touching widgets is safe.
- Scope limited to the genuinely-blocking actions; cheap refreshes stay inline.
