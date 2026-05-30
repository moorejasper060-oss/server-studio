# tests/test_server_detail.py
from server_studio.ui.widgets.server_detail import ServerDetail


class _FakeContentService:
    def search(self, q): return []
    def install(self, r): pass
    def list_installed(self): return []
    def set_enabled(self, f, e): pass
    def remove(self, f): pass


def _detail(qtbot, running=True):
    d = ServerDetail(server_id="abc", name="SkyBlock SMP", version="1.20.6",
                     loader="fabric", running=running)
    qtbot.addWidget(d)
    return d


def test_has_expected_tabs(qtbot):
    d = _detail(qtbot)
    titles = [d.tabs.tabText(i) for i in range(d.tabs.count())]
    assert titles[:2] == ["Console", "Mods"]
    assert "Settings" in titles and "Sharing" in titles


def test_back_button_emits(qtbot):
    d = _detail(qtbot)
    got = []
    d.back_requested.connect(lambda: got.append(True))
    d.back_btn.click()
    assert got == [True]


def test_console_command_forwarded(qtbot):
    d = _detail(qtbot)
    got = []
    d.command_entered.connect(got.append)
    d.console.input.setText("say hi")
    d.console._submit()
    assert got == ["say hi"]


def test_append_console_line(qtbot):
    d = _detail(qtbot)
    d.append_console_line("Done (4.8s)!")
    assert "Done (4.8s)!" in d.console.log.toPlainText()


def test_mods_tab_is_real_when_service_provided(qtbot):
    from server_studio.ui.widgets.mods_tab import ModsTab
    d = ServerDetail(server_id="abc", name="N", version="1.20.6", loader="fabric",
                     running=False, content_service=_FakeContentService())
    qtbot.addWidget(d)
    assert isinstance(d.mods_tab, ModsTab)


def test_mods_tab_is_placeholder_without_service(qtbot):
    d = ServerDetail(server_id="abc", name="N", version="1.20.6", loader="fabric",
                     running=False)
    qtbot.addWidget(d)
    assert d.mods_tab is None


class _FakeSharingService:
    def lan_address(self): return "192.168.1.5:25565"
    def public_address(self): return "203.0.113.7:25565"
    def tunnel_active(self): return False
    def start_tunnel(self, on_address): pass
    def stop_tunnel(self): pass


def test_sharing_tab_real_when_service_provided(qtbot):
    from server_studio.ui.widgets.sharing_tab import SharingTab
    d = ServerDetail(server_id="a", name="N", version="1.20.6", loader="paper",
                     running=False, sharing_service=_FakeSharingService())
    qtbot.addWidget(d)
    assert isinstance(d.sharing_tab, SharingTab)


def test_sharing_tab_placeholder_without_service(qtbot):
    d = ServerDetail(server_id="a", name="N", version="1.20.6", loader="paper", running=False)
    qtbot.addWidget(d)
    assert d.sharing_tab is None


class _FakeBackupService:
    def create(self): return "b.zip"
    def list(self): return []
    def restore(self, name): pass
    def delete(self, name): pass


def test_backups_tab_real_when_service_provided(qtbot):
    from server_studio.ui.widgets.backups_tab import BackupsTab
    d = ServerDetail(server_id="a", name="N", version="1.20.6", loader="paper",
                     running=False, backup_service=_FakeBackupService())
    qtbot.addWidget(d)
    assert isinstance(d.backups_tab, BackupsTab)


def test_backups_tab_placeholder_without_service(qtbot):
    d = ServerDetail(server_id="a", name="N", version="1.20.6", loader="paper", running=False)
    qtbot.addWidget(d)
    assert d.backups_tab is None
