# src/server_studio/app.py
from __future__ import annotations

import httpx

from server_studio.paths import AppPaths
from server_studio.manager import ServerManager
from server_studio.java_manager import JavaManager
from server_studio.process import ServerProcess
from server_studio.installers.registry import build_installer
from server_studio.installers.runner import run_process
from server_studio.temurin import temurin_fetcher


def build_server_manager(paths: AppPaths) -> ServerManager:
    """Construct a fully-wired ServerManager with real network + process backends."""
    paths.ensure()
    client = httpx.Client(follow_redirects=True, timeout=60.0)
    java = JavaManager(paths=paths, fetcher=temurin_fetcher(client))

    return ServerManager(
        paths=paths,
        installer_for=lambda loader: build_installer(loader, client=client, java_resolver=java.resolver, runner=run_process),
        process_factory=ServerProcess,
        java_resolver=java.resolver,
    )


def build_content_services(paths: AppPaths):
    """Return (modrinth_client, content_manager) for the UI mods browser."""
    from server_studio.installers.modrinth import ModrinthClient
    from server_studio.content_manager import ContentManager
    client = httpx.Client(follow_redirects=True, timeout=60.0)
    def downloader(url: str) -> bytes:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.content
    return ModrinthClient(client=client), ContentManager(paths, downloader=downloader)


def build_sharing_factory(bore_path: str = "bore"):
    """Return make(server_id, port) -> SharingService. Public IP resolved once at startup."""
    from pathlib import Path
    from server_studio.sharing.network_info import lan_ip, public_ip
    from server_studio.sharing.tunnel import BoreTunnel
    from server_studio.process import ServerProcess
    from server_studio.ui.sharing_service import SharingService

    try:
        with httpx.Client(timeout=3.0) as client:
            pub = public_ip(client)
    except Exception:
        pub = "unavailable (see whatismyip.com)"

    def make(server_id: str, port: int) -> SharingService:
        def tunnel_factory(on_address):
            return BoreTunnel(port=port, cwd=Path.cwd(), process_factory=ServerProcess,
                              bore_path=bore_path, remote_host="bore.pub", on_address=on_address)
        return SharingService(port=port, public_ip=pub, lan_ip=lan_ip(),
                              tunnel_factory=tunnel_factory)
    return make
