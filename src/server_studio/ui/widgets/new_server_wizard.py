# src/server_studio/ui/widgets/new_server_wizard.py
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QStackedWidget, QWidget, QLabel,
    QPushButton, QComboBox, QLineEdit, QSlider, QButtonGroup,
)

from server_studio.ui.loader_options import loader_options_for_version


class NewServerWizard(QDialog):
    def __init__(self, versions: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Server")
        self._version: str | None = None
        self._loader: str | None = None
        self.loader_buttons: dict[str, QPushButton] = {}
        self._loader_group = QButtonGroup(self)
        self._loader_group.setExclusive(True)

        root = QVBoxLayout(self)
        self.stack = QStackedWidget(self)
        root.addWidget(self.stack, 1)

        # Step 0: version
        s0 = QWidget(); l0 = QVBoxLayout(s0)
        l0.addWidget(QLabel("Choose a Minecraft version"))
        self.version_combo = QComboBox()
        self.version_combo.addItems(versions)
        self.version_combo.currentTextChanged.connect(self.select_version)
        l0.addWidget(self.version_combo)
        if versions:
            self.select_version(versions[0])
        self.stack.addWidget(s0)

        # Step 1: loader (populated when entered)
        self._s1 = QWidget(); self._l1 = QVBoxLayout(self._s1)
        self._l1.addWidget(QLabel("Pick a server type (only valid for this version)"))
        self.stack.addWidget(self._s1)

        # Step 2: configure
        s2 = QWidget(); l2 = QVBoxLayout(s2)
        l2.addWidget(QLabel("Name"))
        self.name_input = QLineEdit()
        l2.addWidget(self.name_input)
        l2.addWidget(QLabel("RAM (MB)"))
        self.ram_slider = QSlider(Qt.Horizontal)
        self.ram_slider.setRange(1024, 16384)
        self.ram_slider.setSingleStep(512)
        self.ram_slider.setValue(2048)
        l2.addWidget(self.ram_slider)
        self.stack.addWidget(s2)

        nav = QHBoxLayout()
        self.back_btn = QPushButton("← Back"); self.back_btn.clicked.connect(self.back_step)
        self.next_btn = QPushButton("Continue →"); self.next_btn.setObjectName("Accent")
        self.next_btn.clicked.connect(self.next_step)
        nav.addWidget(self.back_btn); nav.addStretch(1); nav.addWidget(self.next_btn)
        root.addLayout(nav)

    def select_version(self, version: str) -> None:
        self._version = version

    def select_loader(self, loader_key: str) -> None:
        self._loader = loader_key

    def _build_loader_step(self) -> None:
        for btn in self.loader_buttons.values():
            self._loader_group.removeButton(btn)
            btn.setParent(None)
        self.loader_buttons.clear()
        self._loader = None
        for opt in loader_options_for_version(self._version or ""):
            btn = QPushButton(f"{opt.label}  ({opt.kind})")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, k=opt.key: self.select_loader(k))
            self._loader_group.addButton(btn)
            self._l1.addWidget(btn)
            self.loader_buttons[opt.key] = btn

    def next_step(self) -> None:
        idx = self.stack.currentIndex()
        if idx == 0:
            self._build_loader_step()
        self.stack.setCurrentIndex(min(idx + 1, self.stack.count() - 1))

    def back_step(self) -> None:
        self.stack.setCurrentIndex(max(self.stack.currentIndex() - 1, 0))

    @property
    def result_data(self) -> dict:
        return {
            "name": self.name_input.text().strip(),
            "mc_version": self._version,
            "loader": self._loader,
            "ram_mb": self.ram_slider.value(),
        }
