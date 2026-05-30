import pytest
from server_studio.paths import AppPaths
from server_studio.config import ServerConfig
from server_studio.content_manager import ContentManager


def _server(tmp_path, loader="fabric"):
    paths = AppPaths(root=tmp_path); paths.ensure()
    sdir = paths.server_dir("s1"); sdir.mkdir(parents=True)
    ServerConfig(id="s1", name="S", mc_version="1.20.6", loader=loader).save(sdir / "server.json")
    return paths


def test_install_writes_jar_and_records(tmp_path):
    paths = _server(tmp_path)
    cm = ContentManager(paths, downloader=lambda url: b"JAR")
    cm.install("s1", source="modrinth", project_id="AABB", version_id="v1",
               filename="sodium.jar", url="https://cdn/sodium.jar")
    jar = paths.server_dir("s1") / "mods" / "sodium.jar"
    assert jar.read_bytes() == b"JAR"
    items = cm.list_installed("s1")
    assert items[0]["filename"] == "sodium.jar"
    assert items[0]["enabled"] is True


def test_disable_and_enable(tmp_path):
    paths = _server(tmp_path)
    cm = ContentManager(paths, downloader=lambda url: b"JAR")
    cm.install("s1", source="modrinth", project_id="A", version_id="v1",
               filename="m.jar", url="u")
    cm.set_enabled("s1", "m.jar", False)
    mods = paths.server_dir("s1") / "mods"
    assert (mods / "m.jar.disabled").is_file() and not (mods / "m.jar").exists()
    assert cm.list_installed("s1")[0]["enabled"] is False
    cm.set_enabled("s1", "m.jar", True)
    assert (mods / "m.jar").is_file()


def test_remove(tmp_path):
    paths = _server(tmp_path)
    cm = ContentManager(paths, downloader=lambda url: b"JAR")
    cm.install("s1", source="modrinth", project_id="A", version_id="v1",
               filename="m.jar", url="u")
    cm.remove("s1", "m.jar")
    assert not (paths.server_dir("s1") / "mods" / "m.jar").exists()
    assert cm.list_installed("s1") == []


def test_import_local_jar(tmp_path):
    paths = _server(tmp_path)
    src = tmp_path / "local.jar"; src.write_bytes(b"LOCAL")
    cm = ContentManager(paths, downloader=lambda url: b"")
    cm.import_jar("s1", src)
    assert (paths.server_dir("s1") / "mods" / "local.jar").read_bytes() == b"LOCAL"
    assert cm.list_installed("s1")[0]["source"] == "manual"


def test_install_on_vanilla_raises(tmp_path):
    paths = _server(tmp_path, loader="vanilla")
    cm = ContentManager(paths, downloader=lambda url: b"JAR")
    with pytest.raises(ValueError):
        cm.install("s1", source="modrinth", project_id="A", version_id="v1",
                   filename="m.jar", url="u")
