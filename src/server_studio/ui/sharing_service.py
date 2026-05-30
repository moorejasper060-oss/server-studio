# src/server_studio/ui/sharing_service.py
from __future__ import annotations

from server_studio.sharing.network_info import lan_address


class SharingService:
    """Adapts addresses + a tunnel factory to the SharingTab interface (one server)."""

    def __init__(self, port: int, public_ip: str, lan_ip: str, tunnel_factory):
        self._port = port
        self._public_ip = public_ip
        self._lan_ip = lan_ip
        self._tunnel_factory = tunnel_factory  # (on_address) -> tunnel
        self._tunnel = None

    def lan_address(self) -> str:
        return lan_address(self._port, ip=self._lan_ip)

    def public_address(self) -> str:
        return f"{self._public_ip}:{self._port}"

    def tunnel_active(self) -> bool:
        return self._tunnel is not None and self._tunnel.is_running()

    def start_tunnel(self, on_address) -> None:
        if self._tunnel is not None:
            self._tunnel.stop()
        self._tunnel = self._tunnel_factory(on_address)
        self._tunnel.start()

    def stop_tunnel(self) -> None:
        if self._tunnel:
            self._tunnel.stop()
            self._tunnel = None
