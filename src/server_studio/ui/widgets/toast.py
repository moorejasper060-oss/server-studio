from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation
from PySide6.QtWidgets import QLabel, QGraphicsOpacityEffect


class Toast(QLabel):
    """A transient, non-blocking notification banner."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMargin(12)
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(0.0)
        self.hide()

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(180)

    def show_message(self, text: str, duration_ms: int = 4000) -> None:
        self.setText(text)
        self.adjustSize()
        if self.parent() is not None:
            self._reposition()
        self.show()
        self.raise_()
        self._fade_to(1.0)
        self._hide_timer.start(duration_ms)

    def _fade_to(self, value: float) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._effect.opacity())
        self._anim.setEndValue(value)
        self._anim.start()

    def _fade_out(self) -> None:
        self._fade_to(0.0)
        QTimer.singleShot(220, self.hide)

    def _reposition(self) -> None:
        parent = self.parent()
        if parent is None:
            return
        pr = parent.rect()
        self.move((pr.width() - self.width()) // 2, pr.height() - self.height() - 24)
