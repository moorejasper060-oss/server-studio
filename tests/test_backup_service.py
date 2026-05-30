# tests/test_backup_service.py
from server_studio.ui.backup_service import BackupService


class FakeBM:
    def __init__(self): self.calls = []; self.names = []
    def create_backup(self, sid): self.calls.append(("create", sid)); self.names.append("b.zip"); return "b.zip"
    def list_backups(self, sid): return list(self.names)
    def restore_backup(self, sid, name): self.calls.append(("restore", sid, name))
    def delete_backup(self, sid, name): self.calls.append(("delete", sid, name))


def test_backup_service_delegates():
    bm = FakeBM()
    svc = BackupService(server_id="s1", backup_manager=bm)
    svc.create()
    assert svc.list() == ["b.zip"]
    svc.restore("b.zip"); svc.delete("b.zip")
    assert ("create", "s1") in bm.calls
    assert ("restore", "s1", "b.zip") in bm.calls
    assert ("delete", "s1", "b.zip") in bm.calls
