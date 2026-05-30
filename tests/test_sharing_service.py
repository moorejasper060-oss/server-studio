# tests/test_sharing_service.py
from server_studio.ui.sharing_service import SharingService


class FakeTunnel:
    def __init__(self): self.started = False; self.addr = None
    def start(self): self.started = True
    def is_running(self): return self.started
    def stop(self): self.started = False
    @property
    def address(self): return self.addr


def test_sharing_service_lan_and_public():
    svc = SharingService(port=25565, public_ip="203.0.113.7",
                         lan_ip="192.168.1.5", tunnel_factory=lambda on_addr: FakeTunnel())
    assert svc.lan_address() == "192.168.1.5:25565"
    assert svc.public_address() == "203.0.113.7:25565"
    assert svc.tunnel_active() is False


def test_start_stop_tunnel():
    made = {}
    def factory(on_addr):
        t = FakeTunnel(); made["t"] = t; return t
    svc = SharingService(port=25565, public_ip="x", lan_ip="y", tunnel_factory=factory)
    svc.start_tunnel(lambda a: None)
    assert svc.tunnel_active() is True
    svc.stop_tunnel()
    assert svc.tunnel_active() is False


def test_start_tunnel_stops_previous():
    made = []
    def factory(on_addr):
        t = FakeTunnel(); made.append(t); return t
    svc = SharingService(port=25565, public_ip="x", lan_ip="y", tunnel_factory=factory)
    svc.start_tunnel(lambda a: None)
    svc.start_tunnel(lambda a: None)   # second start
    assert made[0].started is False    # first tunnel was stopped
    assert len(made) == 2
