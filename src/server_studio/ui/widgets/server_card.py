# src/server_studio/ui/widgets/server_card.py
from __future__ import annotations

from PySide6.QtCore import (
    Property, QEasingCurve, QPoint, QPropertyAnimation, Signal,
)
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from server_studio.ui.widgets.status_dot import StatusDot


class ServerCard(QFrame):
    open_requested = Signal(str)
    toggle_requested = Signal(str)

    def __init__(self, *, server_id: str, name: str, version: str, loader: str,
                 running: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self._id = server_id
        self._running = running

        # ── Drop-shadow for hover-lift ──────────────────────────────────────────
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setOffset(0, 2)
        self._shadow.setColor(0x50000000)  # semi-transparent black
        self.setGraphicsEffect(self._shadow)

        # Shadow blur animation (0 → 22 on enter, 22 → 0 on leave).
        self._shadow_anim = QPropertyAnimation(self._shadow, b"blurRadius", self)
        self._shadow_anim.setDuration(120)
        self._shadow_anim.setEasingCurve(QEasingCurve.OutCubic)

        # Y-shift animation (0 → -4 on enter, -4 → 0 on leave).
        # We store the logical lift value in a custom Qt Property and apply it
        # by adjusting the widget's position relative to its natural pos.
        self._lift: int = 0
        self._natural_pos = QPoint(0, 0)
        self._lift_anim = QPropertyAnimation(self, b"_lift_value", self)
        self._lift_anim.setDuration(120)
        self._lift_anim.setEasingCurve(QEasingCurve.OutCubic)

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self._dot = StatusDot(parent=self)
        self.status = QLabel(self)
        self.status.setObjectName("Muted")
        self.badge = QLabel(f"{version} · {loader.title()}", self)
        self.badge.setObjectName("Badge")
        top.addWidget(self._dot)
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

    # ── Custom Qt Property for Y-lift ──────────────────────────────────────────
    def _get_lift(self) -> int:
        return self._lift

    def _set_lift(self, value: int) -> None:
        self._lift = value
        # Shift widget up (negative y) relative to its natural position.
        self.move(self._natural_pos.x(), self._natural_pos.y() - value)

    _lift_value = Property(int, _get_lift, _set_lift)

    # ── Mouse events ───────────────────────────────────────────────────────────
    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._natural_pos = self.pos()

    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        self._natural_pos = self.pos() + QPoint(0, self._lift)  # recalculate natural
        self._animate_hover(entering=True)

    def leaveEvent(self, event) -> None:  # noqa: N802
        super().leaveEvent(event)
        self._animate_hover(entering=False)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        super().mousePressEvent(event)
        # Slight press-down: reduce lift to 1 (instead of 4).
        self._lift_anim.stop()
        self._lift_anim.setStartValue(self._lift)
        self._lift_anim.setEndValue(1)
        self._lift_anim.start()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)
        # Spring back to hover level if cursor still inside.
        self._lift_anim.stop()
        self._lift_anim.setStartValue(self._lift)
        self._lift_anim.setEndValue(4)
        self._lift_anim.start()

    def _animate_hover(self, *, entering: bool) -> None:
        target_blur = 22 if entering else 0
        target_lift = 4 if entering else 0

        self._shadow_anim.stop()
        self._shadow_anim.setStartValue(self._shadow.blurRadius())
        self._shadow_anim.setEndValue(target_blur)
        self._shadow_anim.start()

        self._lift_anim.stop()
        self._lift_anim.setStartValue(self._lift)
        self._lift_anim.setEndValue(target_lift)
        self._lift_anim.start()

    # ── Public API ─────────────────────────────────────────────────────────────
    def set_status(self, running: bool) -> None:
        self._running = running
        self.status.setText("Running" if running else "Stopped")
        self.toggle_btn.setText("■ Stop" if running else "▶ Start")
        self._dot.set_running(running)
