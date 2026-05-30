# src/server_studio/ui/widgets/status_dot.py
"""StatusDot – a small animated status indicator.

When running, a looping QPropertyAnimation pulses the dot's opacity/glow so
the UI feels alive.  When stopped, the dot is a static dim circle.

The ``pulse_phase`` Qt property (0.0 – 1.0) drives the animation; changing it
calls ``update()`` which triggers a repaint.
"""
from __future__ import annotations

import math

from PySide6.QtCore import (
    Property, QEasingCurve, QPropertyAnimation, QSize, Qt,
)
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

from server_studio.ui.theme import DEFAULT_THEME, THEMES

_DEFAULT_RUNNING_COLOR = THEMES[DEFAULT_THEME]["accent"]
_STOPPED_COLOR = "#4a5a4e"

_DOT_RADIUS = 6        # inner filled dot
_HALO_MAX_RADIUS = 12  # outer glow at peak of pulse


class StatusDot(QWidget):
    """A small pulsing dot that signals server running state."""

    def __init__(self, *, color: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self._running = False
        self._color = color or _DEFAULT_RUNNING_COLOR
        self._pulse_phase: float = 0.0

        # Fixed size – 26x26 so the halo has room to breathe.
        self.setFixedSize(QSize(26, 26))
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Animation: cycle pulse_phase 0→1 over 1.4 s, loop forever.
        self._anim = QPropertyAnimation(self, b"pulse_phase")
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(1_400)
        self._anim.setEasingCurve(QEasingCurve.SineCurve)
        self._anim.setLoopCount(-1)  # loop forever

    # ------------------------------------------------------------------ Qt property
    def _get_pulse_phase(self) -> float:
        return self._pulse_phase

    def _set_pulse_phase(self, value: float) -> None:
        self._pulse_phase = value
        self.update()  # request repaint

    pulse_phase = Property(float, _get_pulse_phase, _set_pulse_phase)

    # ------------------------------------------------------------------ public API
    def set_running(self, running: bool) -> None:
        self._running = running
        if running:
            self._anim.start()
        else:
            self._anim.stop()
            self._pulse_phase = 0.0
            self.update()

    def set_color(self, hex_color: str) -> None:
        self._color = hex_color
        self.update()

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------ painting
    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2

        if self._running:
            # Halo: pulsing radial gradient whose radius oscillates via a sine wave.
            # sin is already baked into SineCurve easing, so _pulse_phase goes 0→1
            # smoothly; we map that to a visual radius expansion + alpha fade.
            halo_r = _DOT_RADIUS + (_HALO_MAX_RADIUS - _DOT_RADIUS) * self._pulse_phase
            alpha = int(160 * (1.0 - self._pulse_phase))  # fades out as it expands
            grad = QRadialGradient(cx, cy, halo_r)
            halo_color = QColor(self._color)
            halo_color.setAlpha(alpha)
            grad.setColorAt(0.0, halo_color)
            outer = QColor(self._color)
            outer.setAlpha(0)
            grad.setColorAt(1.0, outer)
            painter.setBrush(grad)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(
                int(cx - halo_r), int(cy - halo_r),
                int(halo_r * 2), int(halo_r * 2),
            )

            # Inner dot – bright accent color.
            dot_color = QColor(self._color)
        else:
            dot_color = QColor(_STOPPED_COLOR)

        painter.setBrush(dot_color)
        painter.setPen(Qt.NoPen)
        r = _DOT_RADIUS
        painter.drawEllipse(int(cx - r), int(cy - r), r * 2, r * 2)
        painter.end()
