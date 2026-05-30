# src/server_studio/ui/widgets/mods_tab.py
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget,
    QListWidgetItem, QLabel,
)

from server_studio.ui.async_runner import run_sync


class ModsTab(QWidget):
    """Search + install mods/plugins and manage installed content via an injected service."""

    def __init__(self, service, task_runner=run_sync, parent=None):
        super().__init__(parent)
        self._service = service
        self._run = task_runner
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
        query = self.search_input.text().strip()
        self._run(lambda: self._service.search(query), self._show_results)

    def _show_results(self, results) -> None:
        self._results = results
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
        self._run(lambda: self._service.install(result), lambda _r: self.refresh_installed())

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
