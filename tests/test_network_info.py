from server_studio.sharing.network_info import lan_address, public_ip


class FakeResp:
    def __init__(self, text): self.text = text
    def raise_for_status(self): return None


class FakeClient:
    def __init__(self, text): self._text = text
    def get(self, url): return FakeResp(self._text)


def test_lan_address_formats_with_given_ip():
    assert lan_address(25565, ip="192.168.1.50") == "192.168.1.50:25565"


def test_lan_address_uses_detected_ip_when_none():
    addr = lan_address(25565)
    assert addr.endswith(":25565")
    assert addr.count(".") == 3  # an IPv4 host


def test_public_ip_reads_client_text():
    assert public_ip(FakeClient("203.0.113.7\n")) == "203.0.113.7"
