# tests/test_theme.py
import pytest
from server_studio.ui.theme import THEMES, THEME_ORDER, DEFAULT_THEME, qss

EXPECTED_KEYS = {
    "grass-green", "diamond-blue", "emerald-teal",
    "nether-amber", "amethyst", "redstone",
}


def test_all_six_themes_present_and_ordered():
    assert set(THEMES) == EXPECTED_KEYS
    assert set(THEME_ORDER) == EXPECTED_KEYS
    assert THEME_ORDER[0] == DEFAULT_THEME == "grass-green"


@pytest.mark.parametrize("key", sorted(EXPECTED_KEYS))
def test_each_theme_defines_full_token_set(key):
    t = THEMES[key]
    for field in ("label", "accent", "accent_dim", "accent_border", "accent_text", "glow"):
        assert field in t and t[field]


@pytest.mark.parametrize("key", sorted(EXPECTED_KEYS))
def test_qss_returns_stylesheet_with_accent(key):
    sheet = qss(key)
    assert isinstance(sheet, str) and len(sheet) > 50
    assert THEMES[key]["accent"] in sheet


def test_qss_unknown_theme_falls_back_to_default():
    assert qss("nope") == qss(DEFAULT_THEME)
