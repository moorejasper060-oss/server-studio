# src/server_studio/ui/widgets/settings_page.py
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QButtonGroup,
)

from server_studio.ui.theme import THEME_ORDER, THEMES


class SettingsPage(QWidget):
    theme_selected = Signal(str)

    def __init__(self, current: str, parent=None):
        super().__init__(parent)
        self.theme_buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        heading = QLabel("Appearance", self)
        f = heading.font(); f.setPointSize(14); f.setBold(True); heading.setFont(f)
        layout.addWidget(heading)
        layout.addWidget(QLabel("Accent theme", self))

        row = QHBoxLayout()
        group = QButtonGroup(self)
        group.setExclusive(True)
        for key in THEME_ORDER:
            btn = QPushButton(THEMES[key]["label"], self)
            btn.setCheckable(True)
            btn.setChecked(key == current)
            btn.clicked.connect(lambda _=False, k=key: self.theme_selected.emit(k))
            group.addButton(btn)
            row.addWidget(btn)
            self.theme_buttons[key] = btn
        layout.addLayout(row)
        layout.addStretch(1)
