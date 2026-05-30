from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton


class SharingTab(QWidget):
    """Shows LAN/public addresses and a one-click internet tunnel toggle."""

    address_received = Signal(str)

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Same network (LAN)", self))
        self.lan_label = QLabel(self._service.lan_address(), self)
        layout.addWidget(self.lan_label)

        layout.addWidget(QLabel("Port-forwarding (advanced)", self))
        self.public_label = QLabel(self._service.public_address(), self)
        layout.addWidget(self.public_label)
        guide = QLabel("Forward this port (TCP) on your router to play over the internet, "
                       "or use the one-click tunnel below.", self)
        guide.setObjectName("Muted")
        guide.setWordWrap(True)
        layout.addWidget(guide)

        layout.addWidget(QLabel("Internet tunnel (one click)", self))
        self.tunnel_label = QLabel("Not shared yet.", self)
        self.tunnel_label.setObjectName("Muted")
        layout.addWidget(self.tunnel_label)

        self.share_btn = QPushButton("🔗 Share over internet", self)
        self.share_btn.setObjectName("Accent")
        self.share_btn.clicked.connect(self._toggle)
        layout.addWidget(self.share_btn)
        layout.addStretch(1)

        self.address_received.connect(self._on_address)
        self._sync()

    def _toggle(self) -> None:
        if self._service.tunnel_active():
            self._service.stop_tunnel()
        else:
            self._service.start_tunnel(self.address_received.emit)
        self._sync()

    def _on_address(self, address: str) -> None:
        self.tunnel_label.setText(f"Friends can join at:  {address}")

    def _sync(self) -> None:
        active = self._service.tunnel_active()
        self.share_btn.setText("■ Stop sharing" if active else "🔗 Share over internet")
        if not active:
            self.tunnel_label.setText("Not shared yet.")
