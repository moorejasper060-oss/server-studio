# tests/test_workers.py
from server_studio.ui.workers import CreateServerWorker


class FakeManagerOK:
    def create_server(self, **kwargs):
        self.kwargs = kwargs
        return {"id": "abc", **kwargs}


class FakeManagerBoom:
    def create_server(self, **kwargs):
        raise RuntimeError("network down")


def test_worker_emits_finished_with_result(qtbot):
    mgr = FakeManagerOK()
    w = CreateServerWorker(mgr, name="SMP", mc_version="1.20.6", loader="paper", ram_mb=4096)
    with qtbot.waitSignal(w.finished, timeout=1000) as blocker:
        w.run()
    assert blocker.args[0]["id"] == "abc"
    assert mgr.kwargs["loader"] == "paper"


def test_worker_emits_failed_on_error(qtbot):
    w = CreateServerWorker(FakeManagerBoom(), name="SMP", mc_version="1.20.6",
                           loader="paper", ram_mb=4096)
    with qtbot.waitSignal(w.failed, timeout=1000) as blocker:
        w.run()
    assert "network down" in blocker.args[0]
