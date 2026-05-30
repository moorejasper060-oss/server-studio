# tests/test_settings_store.py
from server_studio.paths import AppPaths
from server_studio.ui.settings_store import AppSettings
from server_studio.ui.theme import DEFAULT_THEME


def test_defaults_when_missing(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()
    s = AppSettings.load(paths)
    assert s.theme == DEFAULT_THEME


def test_save_then_load_roundtrip(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()
    s = AppSettings.load(paths)
    s.theme = "amethyst"
    s.save(paths)
    assert AppSettings.load(paths).theme == "amethyst"


def test_invalid_theme_falls_back_to_default(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()
    (tmp_path / "settings.json").write_text('{"theme": "bogus"}', encoding="utf-8")
    assert AppSettings.load(paths).theme == DEFAULT_THEME


def test_corrupt_file_falls_back_to_default(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()
    (tmp_path / "settings.json").write_text("not json", encoding="utf-8")
    assert AppSettings.load(paths).theme == DEFAULT_THEME
