from server_studio.ui.widgets.backups_tab import BackupsTab


class FakeService:
    def __init__(self):
        self.backups = []
        self.calls = []
    def create(self):
        self.calls.append("create"); self.backups.append("20260530-120000.zip")
    def list(self):
        return list(self.backups)
    def restore(self, name):
        self.calls.append(("restore", name))
    def delete(self, name):
        self.calls.append(("delete", name)); self.backups = [b for b in self.backups if b != name]


def test_create_backup_refreshes(qtbot):
    svc = FakeService()
    w = BackupsTab(service=svc); qtbot.addWidget(w)
    assert w.backups_list.count() == 0
    w.create_btn.click()
    assert "create" in svc.calls
    assert w.backups_list.count() == 1


def test_refresh_lists_existing(qtbot):
    svc = FakeService(); svc.backups = ["a.zip", "b.zip"]
    w = BackupsTab(service=svc); qtbot.addWidget(w)
    assert w.backups_list.count() == 2


def test_delete_removes(qtbot):
    svc = FakeService(); svc.backups = ["a.zip"]
    w = BackupsTab(service=svc); qtbot.addWidget(w)
    w._delete("a.zip")
    assert ("delete", "a.zip") in svc.calls
    assert w.backups_list.count() == 0


def test_create_error_notifies(qtbot):
    class BoomService(FakeService):
        def create(self):
            raise RuntimeError("no space")
    msgs = []
    w = BackupsTab(service=BoomService(), notify=msgs.append)
    qtbot.addWidget(w)
    w.create_btn.click()
    assert any("no space" in m for m in msgs)
