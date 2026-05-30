# src/server_studio/ui/widgets/console_view.py
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QLineEdit, QLabel,
)

_COLORS = {"warn": "#e0b341", "done": "#39d353", "join": "#7fb3ff", "info": "#aab6ad"}


def _classify(line: str) -> str:
    low = line.lower()
    if "warn" in low:
        return "warn"
    if "joined the game" in low or "left the game" in low:
        return "join"
    if "done (" in low:
        return "done"
    return "info"


class ConsoleView(QWidget):
    """Terminal-style log + command input."""

    command_entered = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.log = QPlainTextEdit(self)
        self.log.setObjectName("Console")
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 1)

        row = QHBoxLayout()
        prompt = QLabel(">", self)
        prompt.setObjectName("Muted")
        self.input = QLineEdit(self)
        self.input.setPlaceholderText("type a server command…")
        self.input.returnPressed.connect(self._submit)
        row.addWidget(prompt)
        row.addWidget(self.input, 1)
        layout.addLayout(row)

    def append_line(self, text: str) -> None:
        color = _COLORS[_classify(text)]
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.log.appendHtml(f'<span style="color:{color}">{safe}</span>')

    def _submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.command_entered.emit(text)
