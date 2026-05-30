# tests/test_mods_tab.py
from server_studio.ui.widgets.mods_tab import ModsTab


class FakeService:
    def __init__(self):
        self.installed = []
        self.results = [{"project_id": "A", "title": "Sodium", "description": "perf"}]
        self.actions = []
    def search(self, query):
        self.actions.append(("search", query))
        return self.results
    def install(self, result):
        self.actions.append(("install", result["project_id"]))
        self.installed.append({"filename": "sodium.jar", "enabled": True})
    def list_installed(self):
        return self.installed
    def set_enabled(self, filename, enabled):
        self.actions.append(("toggle", filename, enabled))
    def remove(self, filename):
        self.actions.append(("remove", filename))
        self.installed = [i for i in self.installed if i["filename"] != filename]


def test_search_populates_results(qtbot):
    svc = FakeService()
    w = ModsTab(service=svc); qtbot.addWidget(w)
    w.search_input.setText("sodium")
    w._do_search()
    assert w.results_list.count() == 1
    assert ("search", "sodium") in svc.actions


def test_install_calls_service_and_refreshes(qtbot):
    svc = FakeService()
    w = ModsTab(service=svc); qtbot.addWidget(w)
    w._do_search()
    w._install_result(svc.results[0])
    assert ("install", "A") in svc.actions
    assert w.installed_list.count() == 1


def test_refresh_lists_installed(qtbot):
    svc = FakeService()
    svc.installed = [{"filename": "x.jar", "enabled": True}]
    w = ModsTab(service=svc); qtbot.addWidget(w)
    w.refresh_installed()
    assert w.installed_list.count() == 1


def test_install_error_notifies(qtbot):
    class BoomService(FakeService):
        def install(self, result):
            raise RuntimeError("disk full")
    msgs = []
    w = ModsTab(service=BoomService(), notify=msgs.append)
    qtbot.addWidget(w)
    w._do_search()
    w._install_result({"project_id": "A", "title": "X", "description": ""})
    assert any("disk full" in m for m in msgs)
