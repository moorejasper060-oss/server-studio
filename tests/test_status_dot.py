# tests/test_status_dot.py
"""Smoke tests for StatusDot – no pixel assertions, just construction + state."""
from server_studio.ui.widgets.status_dot import StatusDot


def test_status_dot_constructs(qtbot):
    dot = StatusDot()
    qtbot.addWidget(dot)
    assert not dot.is_running


def test_set_running_true(qtbot):
    dot = StatusDot()
    qtbot.addWidget(dot)
    dot.set_running(True)
    assert dot.is_running


def test_set_running_false_after_true(qtbot):
    dot = StatusDot()
    qtbot.addWidget(dot)
    dot.set_running(True)
    dot.set_running(False)
    assert not dot.is_running


def test_set_running_false_resets_phase(qtbot):
    dot = StatusDot()
    qtbot.addWidget(dot)
    dot.set_running(True)
    dot.set_running(False)
    assert dot.pulse_phase == 0.0


def test_custom_color(qtbot):
    dot = StatusDot(color="#ff8a3d")
    qtbot.addWidget(dot)
    dot.set_running(True)
    assert dot.is_running


def test_set_color_updates(qtbot):
    dot = StatusDot()
    qtbot.addWidget(dot)
    dot.set_color("#4aa8ff")
    # No crash; state unchanged.
    assert not dot.is_running
