from pathlib import Path
from server_studio.paths import AppPaths


def test_paths_are_under_root_and_created(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()
    assert paths.servers == tmp_path / "servers"
    assert paths.java == tmp_path / "java"
    assert paths.cache == tmp_path / "cache"
    assert paths.backups == tmp_path / "backups"
    for p in (paths.servers, paths.java, paths.cache, paths.backups):
        assert p.is_dir()


def test_server_dir_is_under_servers(tmp_path):
    paths = AppPaths(root=tmp_path)
    assert paths.server_dir("abc") == tmp_path / "servers" / "abc"
