# tests/test_main_window.py
from server_studio.paths import AppPaths
from server_studio.ui.main_window import MainWindow
from server_studio.ui.settings_store import AppSettings


class Cfg:
    def __init__(self, id, name, mc_version, loader):
        self.id, self.name, self.mc_version, self.loader = id, name, mc_version, loader


class FakeManager:
    def __init__(self, servers):
        self._servers = servers
    def list_servers(self):
        return self._servers
    def is_running(self, sid):
        return False


def _win(qtbot, tmp_path, servers=()):
    paths = AppPaths(root=tmp_path); paths.ensure()
    applied = []
    w = MainWindow(manager=FakeManager(list(servers)), paths=paths,
                   apply_theme=applied.append)
    qtbot.addWidget(w)
    return w, applied


def test_dashboard_populated_on_start(qtbot, tmp_path):
    w, _ = _win(qtbot, tmp_path, servers=[Cfg("a", "A", "1.20.6", "paper")])
    assert w.dashboard.card_count() == 1


def test_selecting_theme_persists_and_applies(qtbot, tmp_path):
    w, applied = _win(qtbot, tmp_path)
    w.settings_page.theme_buttons["amethyst"].click()
    assert applied[-1] == "amethyst"
    assert AppSettings.load(w.paths).theme == "amethyst"


def test_open_server_shows_detail(qtbot, tmp_path):
    w, _ = _win(qtbot, tmp_path, servers=[Cfg("a", "A", "1.20.6", "paper")])
    w._open_server("a")
    assert w.stack.currentWidget() is w._detail
    assert w._detail.title.text() == "A"
