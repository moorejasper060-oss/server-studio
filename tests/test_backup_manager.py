import shutil
from datetime import datetime
import pytest
from server_studio.paths import AppPaths
from server_studio.backup_manager import BackupManager


def _server_with_world(tmp_path):
    paths = AppPaths(root=tmp_path); paths.ensure()
    sdir = paths.server_dir("s1"); (sdir / "world").mkdir(parents=True)
    (sdir / "world" / "level.dat").write_bytes(b"WORLD")
    return paths


def test_create_list_restore_delete(tmp_path):
    paths = _server_with_world(tmp_path)
    bm = BackupManager(paths, clock=lambda: datetime(2026, 5, 30, 12, 0, 0))
    name = bm.create_backup("s1")
    assert name.endswith(".zip")
    assert bm.list_backups("s1") == [name]

    name2 = bm.create_backup("s1")        # same clock -> unique suffix
    assert name2 != name
    assert set(bm.list_backups("s1")) == {name, name2}

    shutil.rmtree(paths.server_dir("s1") / "world")
    bm.restore_backup("s1", name)
    assert (paths.server_dir("s1") / "world" / "level.dat").read_bytes() == b"WORLD"

    bm.delete_backup("s1", name)
    assert name not in bm.list_backups("s1")


def test_restore_missing_raises(tmp_path):
    paths = AppPaths(root=tmp_path); paths.ensure()
    paths.server_dir("s1").mkdir(parents=True)
    bm = BackupManager(paths)
    with pytest.raises(FileNotFoundError):
        bm.restore_backup("s1", "nope.zip")


def test_list_empty_when_none(tmp_path):
    paths = AppPaths(root=tmp_path); paths.ensure()
    assert BackupManager(paths).list_backups("s1") == []
