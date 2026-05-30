from __future__ import annotations

import uuid
from pathlib import Path
from typing import Callable

from server_studio.config import ServerConfig
from server_studio.installers.base import Installer
from server_studio.paths import AppPaths


class ServerManager:
    """Façade for creating and controlling servers.

    Dependencies are injected so the core stays testable offline:
      - installer_for: (loader: str) -> installer with
        install(mc_version, dest) -> result(.java_major)
      - process_factory: (command, cwd, on_output) -> process object
        (start(), stop(), is_running())
      - java_resolver: (java_major: int) -> Path to the java executable
    """

    def __init__(self, paths: AppPaths, installer_for: Callable[[str], "Installer"],
                 process_factory: Callable, java_resolver: Callable[[int], Path]):
        self.paths = paths
        self._installer_for = installer_for
        self._process_factory = process_factory
        self._java_resolver = java_resolver
        self._running: dict[str, object] = {}

    def create_server(self, name: str, mc_version: str, loader: str,
                      ram_mb: int = 2048, port: int = 25565) -> ServerConfig:
        server_id = uuid.uuid4().hex[:12]
        server_dir = self.paths.server_dir(server_id)
        server_dir.mkdir(parents=True, exist_ok=True)

        installer = self._installer_for(loader)
        result = installer.install(mc_version, server_dir / "server.jar")
        (server_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
        (server_dir / "server.properties").write_text(
            f"server-port={port}\nmotd=A Minecraft Server (Server Studio)\n",
            encoding="utf-8",
        )

        cfg = ServerConfig(
            id=server_id,
            name=name,
            mc_version=mc_version,
            loader=loader,
            java_runtime=f"temurin-{result.java_major}",
            ram_mb=ram_mb,
            port=port,
            launch_args=result.launch_args,
        )
        cfg.save(server_dir / "server.json")
        return cfg

    def list_servers(self) -> list[ServerConfig]:
        if not self.paths.servers.is_dir():
            return []
        configs = []
        for child in self.paths.servers.iterdir():
            cfg_path = child / "server.json"
            if cfg_path.is_file():
                configs.append(ServerConfig.load(cfg_path))
        return configs

    def get(self, server_id: str) -> ServerConfig:
        return ServerConfig.load(self.paths.server_dir(server_id) / "server.json")

    def _java_major(self, cfg: ServerConfig) -> int:
        runtime = cfg.java_runtime or "temurin-21"
        return int(runtime.split("-")[-1])

    def start_server(self, server_id: str, on_output: Callable[[str], None]) -> None:
        if self.is_running(server_id):
            raise RuntimeError(f"Server {server_id} is already running")
        cfg = self.get(server_id)
        server_dir = self.paths.server_dir(server_id)
        java = self._java_resolver(self._java_major(cfg))
        command = [
            str(java),
            f"-Xmx{cfg.ram_mb}M",
            f"-Xms{min(cfg.ram_mb, 1024)}M",
            *cfg.launch_args,
        ]
        proc = self._process_factory(command, server_dir, on_output)
        proc.start()
        self._running[server_id] = proc

    def is_running(self, server_id: str) -> bool:
        proc = self._running.get(server_id)
        return bool(proc and proc.is_running())

    def stop_server(self, server_id: str) -> None:
        proc = self._running.get(server_id)
        if proc:
            proc.stop()
            self._running.pop(server_id, None)

    def send_command(self, server_id: str, command: str) -> None:
        proc = self._running.get(server_id)
        if proc is None:
            raise RuntimeError(f"Server {server_id} is not running")
        proc.send(command)
