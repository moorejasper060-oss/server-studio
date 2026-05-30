from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
)

from server_studio.ui.async_runner import run_sync


class BackupsTab(QWidget):
    """Create / restore / delete world backups via an injected service."""

    def __init__(self, service, task_runner=run_sync, notify=None, parent=None):
        super().__init__(parent)
        self._service = service
        self._run = task_runner
        self._notify = notify or (lambda _m: None)

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("World backups", self))
        self.create_btn = QPushButton("＋ Backup now", self)
        self.create_btn.setObjectName("Accent")
        self.create_btn.clicked.connect(self._create)
        top.addStretch(1); top.addWidget(self.create_btn)
        layout.addLayout(top)

        self.backups_list = QListWidget(self)
        layout.addWidget(self.backups_list, 1)

        self.refresh()

    def _create(self) -> None:
        self._run(lambda: self._service.create(), lambda _r: self.refresh(),
                  lambda m: self._notify(f"Backup failed: {m}"))

    def refresh(self) -> None:
        self.backups_list.clear()
        for name in self._service.list():
            item = QListWidgetItem()
            row = QWidget(); hl = QHBoxLayout(row); hl.setContentsMargins(0, 0, 0, 0)
            hl.addWidget(QLabel(name), 1)
            restore = QPushButton("Restore")
            restore.clicked.connect(lambda _=False, n=name: self._restore(n))
            delete = QPushButton("Delete")
            delete.clicked.connect(lambda _=False, n=name: self._delete(n))
            hl.addWidget(restore); hl.addWidget(delete)
            self.backups_list.addItem(item)
            self.backups_list.setItemWidget(item, row)

    def _restore(self, name: str) -> None:
        self._run(lambda: self._service.restore(name), lambda _r: self.refresh(),
                  lambda m: self._notify(f"Restore failed: {m}"))

    def _delete(self, name: str) -> None:
        self._service.delete(name)
        self.refresh()
