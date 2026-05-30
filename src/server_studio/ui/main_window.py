# src/server_studio/ui/main_window.py
from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QPushButton,
)

from server_studio.paths import AppPaths
from server_studio.ui.settings_store import AppSettings
from server_studio.ui.widgets.dashboard import Dashboard
from server_studio.ui.widgets.settings_page import SettingsPage
from server_studio.ui.widgets.server_detail import ServerDetail


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
        self.settings_page = SettingsPage(current=self.settings.theme)
        self.settings_page.theme_selected.connect(self._on_theme_selected)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.settings_page)
        root.addWidget(self.stack, 1)

        self.setCentralWidget(central)
        self.refresh()

    def refresh(self) -> None:
        servers = self.manager.list_servers()
        running = {c.id for c in servers if self.manager.is_running(c.id)}
        self.dashboard.set_servers(servers, running_ids=running)

    def _show_dashboard(self) -> None:
        self.stack.setCurrentWidget(self.dashboard)

    def _show_settings(self) -> None:
        self.stack.setCurrentWidget(self.settings_page)

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
        self.stack.addWidget(self._detail)
        self.stack.setCurrentWidget(self._detail)

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

    def _create_server(self, data: dict) -> None:
        self.manager.create_server(
            name=data["name"], mc_version=data["mc_version"],
            loader=data["loader"], ram_mb=data["ram_mb"],
        )
        self.refresh()
