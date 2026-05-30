from __future__ import annotations

import socket

PUBLIC_IP_URL = "https://api.ipify.org"


def lan_ip() -> str:
    """Best-effort local LAN IP (no packets actually sent)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def lan_address(port: int, ip: str | None = None) -> str:
    return f"{ip or lan_ip()}:{port}"


def public_ip(client) -> str:
    resp = client.get(PUBLIC_IP_URL)
    resp.raise_for_status()
    return resp.text.strip()
