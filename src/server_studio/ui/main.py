# src/server_studio/ui/main.py
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from server_studio.paths import AppPaths
from server_studio.app import build_server_manager, build_content_services
from server_studio.ui.main_window import MainWindow
from server_studio.ui.theme import qss


def make_window(manager, paths: AppPaths, apply_theme,
                content_manager=None, search_client=None) -> MainWindow:
    """Build the MainWindow (extracted for testability)."""
    return MainWindow(manager=manager, paths=paths, apply_theme=apply_theme,
                      content_manager=content_manager, search_client=search_client)


def _default_data_root() -> AppPaths:
    return AppPaths(root=Path.home() / ".server-studio")


def main() -> int:
    app = QApplication(sys.argv)
    paths = _default_data_root()
    paths.ensure()
    manager = build_server_manager(paths)
    search_client, content_manager = build_content_services(paths)

    def apply_theme(key: str) -> None:
        app.setStyleSheet(qss(key))

    win = make_window(manager=manager, paths=paths, apply_theme=apply_theme,
                      content_manager=content_manager, search_client=search_client)
    apply_theme(win.settings.theme)
    win.resize(1000, 680)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
