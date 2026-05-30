# tests/test_main_entry.py
from server_studio.paths import AppPaths
from server_studio.ui.main import make_window
from server_studio.ui.theme import qss


class FakeManager:
    def list_servers(self): return []
    def is_running(self, sid): return False


def test_make_window_builds_with_fake_manager(qtbot, tmp_path):
    paths = AppPaths(root=tmp_path); paths.ensure()
    applied = []
    win = make_window(manager=FakeManager(), paths=paths, apply_theme=applied.append)
    qtbot.addWidget(win)
    assert win.windowTitle() == "Server Studio"


def test_qss_smoke_for_app():
    assert "QWidget" in qss("grass-green")
