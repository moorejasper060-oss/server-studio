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
    """Runs fn() on a QThread; delivers on_done/on_error on the UI thread via signals.

    Each call gets its own signals object, so callbacks never accumulate or cross-fire
    when one AsyncRunner instance is shared across the app.
    """

    def __init__(self):
        self._active: list = []  # keep (worker, signals) alive until completion

    def __call__(self, fn, on_done, on_error=None) -> None:
        signals = _Signals()
        worker = _Worker(fn, signals)
        signals.done.connect(on_done)
        if on_error:
            signals.failed.connect(on_error)
        signals.done.connect(lambda *_: self._cleanup(worker))
        signals.failed.connect(lambda *_: self._cleanup(worker))
        self._active.append((worker, signals))
        worker.start()

    def _cleanup(self, worker) -> None:
        self._active = [(w, s) for (w, s) in self._active if w is not worker]
