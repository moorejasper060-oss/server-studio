from server_studio.ui.widgets.sharing_tab import SharingTab


class FakeService:
    def __init__(self):
        self.active = False
        self.calls = []
        self._cb = None
    def lan_address(self): return "192.168.1.5:25565"
    def public_address(self): return "203.0.113.7:25565"
    def tunnel_active(self): return self.active
    def start_tunnel(self, on_address):
        self.active = True; self.calls.append("start"); self._cb = on_address
        on_address("bore.pub:45678")
    def stop_tunnel(self):
        self.active = False; self.calls.append("stop")


def test_shows_lan_and_public(qtbot):
    w = SharingTab(service=FakeService()); qtbot.addWidget(w)
    assert "192.168.1.5:25565" in w.lan_label.text()
    assert "203.0.113.7:25565" in w.public_label.text()


def test_share_button_starts_tunnel_and_shows_address(qtbot):
    svc = FakeService()
    w = SharingTab(service=svc); qtbot.addWidget(w)
    w.share_btn.click()
    assert "start" in svc.calls
    assert "bore.pub:45678" in w.tunnel_label.text()
    # button now offers to stop
    assert "Stop" in w.share_btn.text()


def test_share_button_toggles_off(qtbot):
    svc = FakeService()
    w = SharingTab(service=svc); qtbot.addWidget(w)
    w.share_btn.click()   # start
    w.share_btn.click()   # stop
    assert svc.calls == ["start", "stop"]
