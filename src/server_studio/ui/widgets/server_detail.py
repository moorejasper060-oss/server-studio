# src/server_studio/ui/widgets/server_detail.py
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
)

from server_studio.ui.widgets.console_view import ConsoleView


class ServerDetail(QWidget):
    back_requested = Signal()
    toggle_requested = Signal(str)
    command_entered = Signal(str)

    def __init__(self, *, server_id: str, name: str, version: str, loader: str,
                 running: bool, parent=None):
        super().__init__(parent)
        self._id = server_id

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.back_btn = QPushButton("←", self)
        self.back_btn.clicked.connect(self.back_requested.emit)
        self.title = QLabel(name, self)
        f = self.title.font(); f.setPointSize(14); f.setBold(True); self.title.setFont(f)
        self.badge = QLabel(f"{version} · {loader.title()}", self)
        self.badge.setObjectName("Badge")
        self.toggle_btn = QPushButton(self)
        self.toggle_btn.clicked.connect(lambda: self.toggle_requested.emit(self._id))
        header.addWidget(self.back_btn)
        header.addWidget(self.title)
        header.addWidget(self.badge)
        header.addStretch(1)
        header.addWidget(self.toggle_btn)
        layout.addLayout(header)

        self.tabs = QTabWidget(self)
        self.console = ConsoleView(self)
        self.console.command_entered.connect(self.command_entered.emit)
        self.tabs.addTab(self.console, "Console")
        self.tabs.addTab(self._placeholder("Mods browser arrives in a later update."), "Mods")
        self.tabs.addTab(self._placeholder("Server settings."), "Settings")
        self.tabs.addTab(self._placeholder("Connected players."), "Players")
        self.tabs.addTab(self._placeholder("World backups arrive in a later update."), "Backups")
        self.tabs.addTab(self._placeholder("Invite friends arrives in a later update."), "Sharing")
        layout.addWidget(self.tabs, 1)

        self.set_status(running)

    def _placeholder(self, text: str) -> QWidget:
        w = QWidget(); l = QVBoxLayout(w)
        label = QLabel(text); label.setObjectName("Muted")
        l.addWidget(label); l.addStretch(1)
        return w

    def set_status(self, running: bool) -> None:
        self.toggle_btn.setText("■ Stop" if running else "▶ Start")

    def append_console_line(self, text: str) -> None:
        self.console.append_line(text)

    @property
    def server_id(self) -> str:
        return self._id
