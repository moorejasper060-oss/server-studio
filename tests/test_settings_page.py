# tests/test_settings_page.py
from server_studio.ui.widgets.settings_page import SettingsPage
from server_studio.ui.theme import THEME_ORDER


def test_has_button_per_theme(qtbot):
    p = SettingsPage(current="grass-green")
    qtbot.addWidget(p)
    assert set(p.theme_buttons) == set(THEME_ORDER)


def test_selecting_theme_emits_key(qtbot):
    p = SettingsPage(current="grass-green")
    qtbot.addWidget(p)
    got = []
    p.theme_selected.connect(got.append)
    p.theme_buttons["amethyst"].click()
    assert got == ["amethyst"]


def test_current_theme_is_checked(qtbot):
    p = SettingsPage(current="redstone")
    qtbot.addWidget(p)
    assert p.theme_buttons["redstone"].isChecked()
    assert not p.theme_buttons["grass-green"].isChecked()
