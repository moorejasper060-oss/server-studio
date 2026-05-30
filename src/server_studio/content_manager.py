# src/server_studio/content_manager.py
from __future__ import annotations

from pathlib import Path
from typing import Callable

from server_studio.config import ServerConfig
from server_studio.paths import AppPaths
from server_studio.installers.content_target import content_dir_name


class ContentManager:
    """Manages a server's installed mods/plugins (files + config records)."""

    def __init__(self, paths: AppPaths, downloader: Callable[[str], bytes]):
        self._paths = paths
        self._downloader = downloader

    def _cfg_path(self, server_id: str) -> Path:
        return self._paths.server_dir(server_id) / "server.json"

    def _load(self, server_id: str) -> ServerConfig:
        return ServerConfig.load(self._cfg_path(server_id))

    def _content_dir(self, cfg: ServerConfig) -> Path:
        name = content_dir_name(cfg.loader)
        if name is None:
            raise ValueError(f"{cfg.loader} servers do not support mods or plugins")
        d = self._paths.server_dir(cfg.id) / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def list_installed(self, server_id: str) -> list[dict]:
        return self._load(server_id).installed_content

    def install(self, server_id: str, *, source: str, project_id: str, version_id: str,
                filename: str, url: str) -> None:
        cfg = self._load(server_id)
        target = self._content_dir(cfg) / filename
        target.write_bytes(self._downloader(url))
        cfg.installed_content.append({
            "source": source, "project_id": project_id, "version_id": version_id,
            "filename": filename, "enabled": True,
        })
        cfg.save(self._cfg_path(server_id))

    def import_jar(self, server_id: str, src: Path) -> None:
        cfg = self._load(server_id)
        target = self._content_dir(cfg) / src.name
        target.write_bytes(src.read_bytes())
        cfg.installed_content.append({
            "source": "manual", "project_id": None, "version_id": None,
            "filename": src.name, "enabled": True,
        })
        cfg.save(self._cfg_path(server_id))

    def set_enabled(self, server_id: str, filename: str, enabled: bool) -> None:
        cfg = self._load(server_id)
        d = self._content_dir(cfg)
        active, disabled = d / filename, d / f"{filename}.disabled"
        if enabled and disabled.is_file():
            disabled.rename(active)
        elif not enabled and active.is_file():
            active.rename(disabled)
        for item in cfg.installed_content:
            if item["filename"] == filename:
                item["enabled"] = enabled
        cfg.save(self._cfg_path(server_id))

    def remove(self, server_id: str, filename: str) -> None:
        cfg = self._load(server_id)
        d = self._content_dir(cfg)
        for candidate in (d / filename, d / f"{filename}.disabled"):
            if candidate.is_file():
                candidate.unlink()
        cfg.installed_content = [i for i in cfg.installed_content if i["filename"] != filename]
        cfg.save(self._cfg_path(server_id))
