# src/server_studio/ui/main_window.py
from __future__ import annotations

import threading
from typing import Callable

from PySide6.QtCore import (
    QEasingCurve, QObject, QPropertyAnimation, QSequentialAnimationGroup, Signal, QThread,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QPushButton,
)

from server_studio.paths import AppPaths
from server_studio.ui.settings_store import AppSettings
from server_studio.ui.widgets.dashboard import Dashboard
from server_studio.ui.widgets.settings_page import SettingsPage
from server_studio.ui.widgets.server_detail import ServerDetail


class _ConsoleBridge(QObject):
    """Marshals server stdout (emitted from ServerProcess's reader thread) onto the UI thread.

    Carries (server_id, line) so output is routed only to the matching server's console.
    """
    line = Signal(str, str)


class _StopBridge(QObject):
    """Signals (on the UI thread) that an async stop has completed."""
    done = Signal(str)


class MainWindow(QMainWindow):
    def __init__(self, manager, paths: AppPaths, apply_theme: Callable[[str], None],
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Server Studio")
        self.manager = manager
        self.paths = paths
        self._apply_theme = apply_theme
        self.settings = AppSettings.load(paths)
        self._detail: ServerDetail | None = None
        self._wizard = None
        self._create_thread = None
        self._create_worker = None
        self._last_create_error = None
        self._console_bridge = _ConsoleBridge()
        self._console_bridge.line.connect(self._on_console_line)
        self._stop_bridge = _StopBridge()
        self._stop_bridge.done.connect(self._on_server_stopped)

        central = QWidget(); root = QHBoxLayout(central)

        rail = QVBoxLayout()
        self.nav_dash = QPushButton("▤"); self.nav_dash.clicked.connect(self._show_dashboard)
        self.nav_settings = QPushButton("⚙"); self.nav_settings.clicked.connect(self._show_settings)
        rail.addWidget(self.nav_dash); rail.addStretch(1); rail.addWidget(self.nav_settings)
        root.addLayout(rail)

        self.stack = QStackedWidget()
        self.dashboard = Dashboard()
        self.dashboard.open_requested.connect(self._open_server)
        self.dashboard.new_requested.connect(self._start_new_server)
        self.dashboard.toggle_requested.connect(self._toggle_server)
        self.settings_page = SettingsPage(current=self.settings.theme)
        self.settings_page.theme_selected.connect(self._on_theme_selected)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.settings_page)
        root.addWidget(self.stack, 1)

        # ── Per-page opacity effects for cross-fade ────────────────────────────
        # We keep one reusable animation; switching a page fades out the current
        # one, swaps, then fades the new one in – all via _fade_to().
        self._page_anim: QPropertyAnimation | None = None

        self.setCentralWidget(central)
        self.refresh()

    # ── Page transition ────────────────────────────────────────────────────────
    def _fade_to(self, widget: QWidget) -> None:
        """Cross-fade the stack to *widget* (~150 ms total).

        The stack swap is **immediate** (so tests relying on currentWidget()
        right after the call still pass).  The fade is a purely cosmetic layer
        applied on top via QGraphicsOpacityEffect.
        """
        if self.stack.currentWidget() is widget:
            return

        current = self.stack.currentWidget()

        # Ensure both widgets have opacity effects.
        def _ensure_effect(w: QWidget, initial_opacity: float) -> QGraphicsOpacityEffect:
            eff = w.graphicsEffect()
            if not isinstance(eff, QGraphicsOpacityEffect):
                eff = QGraphicsOpacityEffect(w)
                eff.setOpacity(initial_opacity)
                w.setGraphicsEffect(eff)
            return eff

        if current is not None:
            out_eff = _ensure_effect(current, 1.0)
        in_eff = _ensure_effect(widget, 0.0)

        # Abort any running animation first.
        if self._page_anim is not None:
            self._page_anim.stop()

        # ── Swap immediately (tests can check currentWidget right away) ────────
        self.stack.setCurrentWidget(widget)

        # ── Then animate: fade in the new page (75 ms) ────────────────────────
        in_eff.setOpacity(0.0)
        anim_in = QPropertyAnimation(in_eff, b"opacity", self)
        anim_in.setDuration(75)
        anim_in.setStartValue(0.0)
        anim_in.setEndValue(1.0)
        anim_in.setEasingCurve(QEasingCurve.OutCubic)
        self._page_anim = anim_in
        anim_in.start()

        # Also restore the outgoing page's opacity for the next time it appears.
        if current is not None:
            out_eff.setOpacity(1.0)

    # ── Navigation ─────────────────────────────────────────────────────────────
    def refresh(self) -> None:
        servers = self.manager.list_servers()
        running = {c.id for c in servers if self.manager.is_running(c.id)}
        self.dashboard.set_servers(servers, running_ids=running)

    def _show_dashboard(self) -> None:
        self._fade_to(self.dashboard)

    def _show_settings(self) -> None:
        self._fade_to(self.settings_page)

    def _on_theme_selected(self, key: str) -> None:
        self.settings.theme = key
        self.settings.save(self.paths)
        self._apply_theme(key)

    def _open_server(self, server_id: str) -> None:
        cfg = next(c for c in self.manager.list_servers() if c.id == server_id)
        if self._detail is not None:
            self._detail.setParent(None)
        self._detail = ServerDetail(server_id=cfg.id, name=cfg.name, version=cfg.mc_version,
                                    loader=cfg.loader, running=self.manager.is_running(cfg.id))
        self._detail.back_requested.connect(self._show_dashboard)
        self._detail.toggle_requested.connect(self._toggle_server)
        sid = cfg.id
        self._detail.command_entered.connect(lambda text: self._send_command(sid, text))
        self.stack.addWidget(self._detail)
        self._fade_to(self._detail)

    def open_new_server_dialog(self, versions, on_create) -> None:
        """versions: list[str]; on_create: callable(result_dict) -> None."""
        from server_studio.ui.widgets.new_server_wizard import NewServerWizard
        dlg = NewServerWizard(versions=versions, parent=self)
        dlg.next_btn.clicked.connect(
            lambda: self._maybe_finish_wizard(dlg, on_create)
        )
        dlg.show()
        self._wizard = dlg

    def _maybe_finish_wizard(self, dlg, on_create) -> None:
        # On the final step, "Continue" acts as "Create".
        if dlg.stack.currentIndex() == dlg.stack.count() - 1:
            on_create(dlg.result_data)
            dlg.accept()

    def _start_new_server(self) -> None:
        versions = getattr(self, "_versions", ["1.21.4", "1.20.6", "1.20.4", "1.16.5"])
        self.open_new_server_dialog(versions, self._create_server)

    def _send_command(self, server_id: str, text: str) -> None:
        if self.manager.is_running(server_id):
            self.manager.send_command(server_id, text)

    def _create_server(self, data: dict) -> None:
        from server_studio.ui.workers import CreateServerWorker
        thread = QThread()
        worker = CreateServerWorker(
            self.manager, name=data["name"], mc_version=data["mc_version"],
            loader=data["loader"], ram_mb=data["ram_mb"],
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_create_finished)
        worker.failed.connect(self._on_create_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        # keep references so the thread/worker aren't garbage-collected mid-run
        self._create_thread = thread
        self._create_worker = worker
        thread.start()

    def _on_create_finished(self, cfg) -> None:
        self.refresh()

    def _on_create_failed(self, message: str) -> None:
        # Surfaced to the user via a toast in the real app; stored for now.
        self._last_create_error = message

    def _toggle_server(self, server_id: str) -> None:
        if self.manager.is_running(server_id):
            # Stopping a Minecraft server can block for seconds — do it off the UI thread.
            def _run() -> None:
                self.manager.stop_server(server_id)
                self._stop_bridge.done.emit(server_id)
            threading.Thread(target=_run, daemon=True).start()
        else:
            self.manager.start_server(
                server_id,
                on_output=lambda line, sid=server_id: self._console_bridge.line.emit(sid, line),
            )
            self.refresh()
            self._sync_detail_status(server_id)

    def _on_server_stopped(self, server_id: str) -> None:
        self.refresh()
        self._sync_detail_status(server_id)

    def _sync_detail_status(self, server_id: str) -> None:
        if self._detail is not None and self._detail.server_id == server_id:
            self._detail.set_status(self.manager.is_running(server_id))

    def _on_console_line(self, server_id: str, text: str) -> None:
        if self._detail is not None and self._detail.server_id == server_id:
            self._detail.append_console_line(text)
