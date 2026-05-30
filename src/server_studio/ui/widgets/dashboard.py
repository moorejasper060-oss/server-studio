# src/server_studio/ui/widgets/dashboard.py
from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QScrollArea,
)

from server_studio.ui.widgets.server_card import ServerCard


class Dashboard(QWidget):
    new_requested = Signal()
    open_requested = Signal(str)
    toggle_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: dict[str, ServerCard] = {}

        outer = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Your Servers", self)
        f = title.font(); f.setPointSize(15); f.setBold(True); title.setFont(f)
        self.new_btn = QPushButton("＋ New Server", self)
        self.new_btn.setObjectName("Accent")
        self.new_btn.clicked.connect(self.new_requested.emit)
        header.addWidget(title); header.addStretch(1); header.addWidget(self.new_btn)
        outer.addLayout(header)

        self.empty_label = QLabel("No servers yet — create your first one!", self)
        self.empty_label.setObjectName("Muted")
        self.empty_label.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.empty_label)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._scroll.setWidget(self._grid_host)
        outer.addWidget(self._scroll, 1)

        self.show()

    def card_count(self) -> int:
        return len(self._cards)

    def set_servers(self, configs, running_ids) -> None:
        for card in self._cards.values():
            card.setParent(None)
        self._cards.clear()

        for i, cfg in enumerate(configs):
            card = ServerCard(server_id=cfg.id, name=cfg.name, version=cfg.mc_version,
                              loader=cfg.loader, running=cfg.id in running_ids)
            card.open_requested.connect(self.open_requested.emit)
            card.toggle_requested.connect(self.toggle_requested.emit)
            self._grid.addWidget(card, i // 2, i % 2)
            self._cards[cfg.id] = card

        self.empty_label.setVisible(not configs)
        self._scroll.setVisible(bool(configs))
