# src/server_studio/ui/widgets/server_detail.py
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QGraphicsOpacityEffect,
)

from server_studio.ui.widgets.console_view import ConsoleView
from server_studio.ui.widgets.status_dot import StatusDot


class ServerDetail(QWidget):
    back_requested = Signal()
    toggle_requested = Signal(str)
    command_entered = Signal(str)

    def __init__(self, *, server_id: str, name: str, version: str, loader: str,
                 running: bool, parent=None):
        super().__init__(parent)
        self._id = server_id

        layout = QVBoxLayout(self)

        # ── Header ─────────────────────────────────────────────────────────────
        header = QHBoxLayout()
        self.back_btn = QPushButton("←", self)
        self.back_btn.clicked.connect(self.back_requested.emit)
        self._dot = StatusDot(parent=self)
        self.title = QLabel(name, self)
        f = self.title.font(); f.setPointSize(14); f.setBold(True); self.title.setFont(f)
        self.badge = QLabel(f"{version} · {loader.title()}", self)
        self.badge.setObjectName("Badge")
        self.toggle_btn = QPushButton(self)
        self.toggle_btn.clicked.connect(lambda: self.toggle_requested.emit(self._id))
        header.addWidget(self.back_btn)
        header.addWidget(self._dot)
        header.addWidget(self.title)
        header.addWidget(self.badge)
        header.addStretch(1)
        header.addWidget(self.toggle_btn)
        layout.addLayout(header)

        # ── Tabs ───────────────────────────────────────────────────────────────
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

        # ── Tab cross-fade ─────────────────────────────────────────────────────
        # Apply an opacity effect to the tab widget content area and fade on change.
        self._tab_opacity = QGraphicsOpacityEffect(self.tabs)
        self._tab_opacity.setOpacity(1.0)
        self.tabs.setGraphicsEffect(self._tab_opacity)
        self._tab_anim = QPropertyAnimation(self._tab_opacity, b"opacity", self)
        self._tab_anim.setDuration(120)
        self._tab_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.set_status(running)

    def _placeholder(self, text: str) -> QWidget:
        w = QWidget(); l = QVBoxLayout(w)
        label = QLabel(text); label.setObjectName("Muted")
        l.addWidget(label); l.addStretch(1)
        return w

    def _on_tab_changed(self, _index: int) -> None:
        """Quick opacity dip (0.3→1.0) when the user switches tabs."""
        self._tab_anim.stop()
        self._tab_opacity.setOpacity(0.3)
        self._tab_anim.setStartValue(0.3)
        self._tab_anim.setEndValue(1.0)
        self._tab_anim.start()

    def set_status(self, running: bool) -> None:
        self.toggle_btn.setText("■ Stop" if running else "▶ Start")
        self._dot.set_running(running)

    def append_console_line(self, text: str) -> None:
        self.console.append_line(text)

    @property
    def server_id(self) -> str:
        return self._id
