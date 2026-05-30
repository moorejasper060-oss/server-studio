# src/server_studio/ui/widgets/server_card.py
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton


class ServerCard(QFrame):
    open_requested = Signal(str)
    toggle_requested = Signal(str)

    def __init__(self, *, server_id: str, name: str, version: str, loader: str,
                 running: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self._id = server_id
        self._running = running

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.status = QLabel(self)
        self.status.setObjectName("Muted")
        self.badge = QLabel(f"{version} · {loader.title()}", self)
        self.badge.setObjectName("Badge")
        top.addWidget(self.status)
        top.addStretch(1)
        top.addWidget(self.badge)
        layout.addLayout(top)

        self.name_label = QLabel(name, self)
        f = self.name_label.font()
        f.setPointSize(13)
        f.setBold(True)
        self.name_label.setFont(f)
        layout.addWidget(self.name_label)

        actions = QHBoxLayout()
        self.toggle_btn = QPushButton(self)
        self.open_btn = QPushButton("Open →", self)
        self.open_btn.setObjectName("AccentGhost")
        self.toggle_btn.clicked.connect(lambda: self.toggle_requested.emit(self._id))
        self.open_btn.clicked.connect(lambda: self.open_requested.emit(self._id))
        actions.addWidget(self.toggle_btn)
        actions.addWidget(self.open_btn)
        layout.addLayout(actions)

        self.set_status(running)

    def set_status(self, running: bool) -> None:
        self._running = running
        self.status.setText("● Running" if running else "○ Stopped")
        self.toggle_btn.setText("■ Stop" if running else "▶ Start")
