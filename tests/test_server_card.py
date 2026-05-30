# tests/test_server_card.py
from server_studio.ui.widgets.server_card import ServerCard


def _card(qtbot, running=False):
    c = ServerCard(server_id="abc", name="SkyBlock SMP",
                   version="1.20.6", loader="fabric", running=running)
    qtbot.addWidget(c)
    return c


def test_card_shows_name_and_badge(qtbot):
    c = _card(qtbot)
    assert "SkyBlock SMP" in c.name_label.text()
    assert "1.20.6" in c.badge.text() and "fabric" in c.badge.text().lower()


def test_open_button_emits_id(qtbot):
    c = _card(qtbot)
    got = []
    c.open_requested.connect(got.append)
    c.open_btn.click()
    assert got == ["abc"]


def test_toggle_button_label_reflects_state(qtbot):
    stopped = _card(qtbot, running=False)
    assert stopped.toggle_btn.text().lower().startswith(("▶", "start")) or "Start" in stopped.toggle_btn.text()
    running = _card(qtbot, running=True)
    assert "Stop" in running.toggle_btn.text()


def test_toggle_emits_id(qtbot):
    c = _card(qtbot)
    got = []
    c.toggle_requested.connect(got.append)
    c.toggle_btn.click()
    assert got == ["abc"]
