# tests/test_toggle_stream.py
from server_studio.paths import AppPaths
from server_studio.ui.main_window import MainWindow


class Cfg:
    def __init__(self, id, name, mc_version, loader):
        self.id, self.name, self.mc_version, self.loader = id, name, mc_version, loader


class StreamingManager:
    def __init__(self, servers):
        self._servers = servers
        self._running = set()
        self.captured_on_output = None

    def list_servers(self):
        return self._servers

    def is_running(self, sid):
        return sid in self._running

    def start_server(self, sid, on_output):
        self._running.add(sid)
        self.captured_on_output = on_output
        on_output("Done (4.8s)! For help, type help")

    def stop_server(self, sid):
        self._running.discard(sid)


def _win(qtbot, tmp_path, mgr):
    paths = AppPaths(root=tmp_path); paths.ensure()
    w = MainWindow(manager=mgr, paths=paths, apply_theme=lambda k: None)
    qtbot.addWidget(w)
    return w


def test_toggle_starts_streams_and_stops(qtbot, tmp_path):
    mgr = StreamingManager([Cfg("a", "A", "1.20.6", "paper")])
    w = _win(qtbot, tmp_path, mgr)
    w._open_server("a")

    w._toggle_server("a")  # start
    assert mgr.is_running("a")
    assert "Done (4.8s)!" in w._detail.console.log.toPlainText()
    assert "■ Stop" in w._detail.toggle_btn.text()

    w._toggle_server("a")  # stop
    assert not mgr.is_running("a")
    assert "▶ Start" in w._detail.toggle_btn.text()


def test_dashboard_toggle_signal_wired(qtbot, tmp_path):
    mgr = StreamingManager([Cfg("a", "A", "1.20.6", "paper")])
    w = _win(qtbot, tmp_path, mgr)
    # clicking a card's toggle should start the server via the wired signal
    w.dashboard._cards["a"].toggle_btn.click()
    assert mgr.is_running("a")
