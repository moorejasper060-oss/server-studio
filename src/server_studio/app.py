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
