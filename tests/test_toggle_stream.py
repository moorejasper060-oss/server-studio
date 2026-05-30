# tests/test_toggle_stream.py
import threading

from server_studio.paths import AppPaths
from server_studio.ui.main_window import MainWindow


class Cfg:
    def __init__(self, id, name, mc_version, loader):
        self.id, self.name, self.mc_version, self.loader = id, name, mc_version, loader


class StreamingManager:
    def __init__(self, servers):
        self._servers = servers
        self._running = set()

    def list_servers(self):
        return self._servers

    def is_running(self, sid):
        return sid in self._running

    def start_server(self, sid, on_output):
        self._running.add(sid)
        on_output("Done (4.8s)! For help, type help")

    def stop_server(self, sid):
        self._running.discard(sid)


def _win(qtbot, tmp_path, mgr):
    paths = AppPaths(root=tmp_path); paths.ensure()
    w = MainWindow(manager=mgr, paths=paths, apply_theme=lambda k: None)
    qtbot.addWidget(w)
    return w


def test_toggle_starts_and_streams(qtbot, tmp_path):
    mgr = StreamingManager([Cfg("a", "A", "1.20.6", "paper")])
    w = _win(qtbot, tmp_path, mgr)
    w._open_server("a")
    w._toggle_server("a")  # start (synchronous in fake)
    assert mgr.is_running("a")
    assert "Done (4.8s)!" in w._detail.console.log.toPlainText()
    assert "■ Stop" in w._detail.toggle_btn.text()


def test_toggle_stop_runs_async_and_updates(qtbot, tmp_path):
    mgr = StreamingManager([Cfg("a", "A", "1.20.6", "paper")])
    w = _win(qtbot, tmp_path, mgr)
    w._open_server("a")
    w._toggle_server("a")  # start
    with qtbot.waitSignal(w._stop_bridge.done, timeout=2000):
        w._toggle_server("a")  # stop (async)
    assert not mgr.is_running("a")
    qtbot.waitUntil(lambda: "▶ Start" in w._detail.toggle_btn.text(), timeout=2000)


def test_dashboard_toggle_signal_wired(qtbot, tmp_path):
    mgr = StreamingManager([Cfg("a", "A", "1.20.6", "paper")])
    w = _win(qtbot, tmp_path, mgr)
    w.dashboard._cards["a"].toggle_btn.click()
    assert mgr.is_running("a")


def test_console_does_not_bleed_across_servers(qtbot, tmp_path):
    mgr = StreamingManager([Cfg("a", "A", "1.20.6", "paper"),
                            Cfg("b", "B", "1.20.6", "paper")])
    w = _win(qtbot, tmp_path, mgr)
    w._open_server("b")          # B's detail is open
    w._toggle_server("a")        # but we start A
    # A's output must NOT appear in B's console
    assert "Done (4.8s)!" not in w._detail.console.log.toPlainText()


def test_console_streams_from_worker_thread(qtbot, tmp_path):
    class ThreadedManager(StreamingManager):
        def start_server(self, sid, on_output):
            self._running.add(sid)
            t = threading.Thread(target=lambda: on_output("Threaded line!"))
            t.start(); t.join()

    mgr = ThreadedManager([Cfg("a", "A", "1.20.6", "paper")])
    w = _win(qtbot, tmp_path, mgr)
    w._open_server("a")
    w._toggle_server("a")
    qtbot.waitUntil(
        lambda: "Threaded line!" in w._detail.console.log.toPlainText(), timeout=2000
    )
