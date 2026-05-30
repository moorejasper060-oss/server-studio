from pathlib import Path
from server_studio.sharing.tunnel import BoreTunnel


class FakeProc:
    def __init__(self, command, cwd, on_output):
        self.command = command
        self._on_output = on_output
        self.running = False
        self.stopped = False
    def start(self):
        self.running = True
        # bore prints this once the tunnel is established
        self._on_output("2025-01-01 INFO listening at bore.pub:45678")
    def is_running(self):
        return self.running
    def stop(self, timeout=10.0):
        self.stopped = True
        self.running = False


def test_start_parses_address(tmp_path):
    procs = []
    def factory(command, cwd, on_output):
        p = FakeProc(command, cwd, on_output); procs.append(p); return p
    got = []
    t = BoreTunnel(port=25565, cwd=tmp_path, process_factory=factory,
                   bore_path="bore", remote_host="bore.pub", on_address=got.append)
    t.start()
    assert t.address == "bore.pub:45678"
    assert got == ["bore.pub:45678"]
    # command is correct
    assert procs[0].command == ["bore", "local", "25565", "--to", "bore.pub"]
    assert t.is_running() is True


def test_stop(tmp_path):
    def factory(command, cwd, on_output):
        return FakeProc(command, cwd, on_output)
    t = BoreTunnel(port=25565, cwd=tmp_path, process_factory=factory)
    t.start()
    t.stop()
    assert t.is_running() is False


def test_address_none_before_start(tmp_path):
    t = BoreTunnel(port=25565, cwd=tmp_path,
                   process_factory=lambda c, d, o: FakeProc(c, d, o))
    assert t.address is None
