from server_studio.config import ServerConfig


def test_roundtrip_to_and_from_dict():
    cfg = ServerConfig(
        id="abc",
        name="My SMP",
        mc_version="1.20.6",
        loader="vanilla",
        ram_mb=4096,
        port=25565,
    )
    data = cfg.to_dict()
    restored = ServerConfig.from_dict(data)
    assert restored == cfg


def test_save_and_load_file(tmp_path):
    cfg = ServerConfig(id="abc", name="My SMP", mc_version="1.20.6", loader="vanilla")
    path = tmp_path / "server.json"
    cfg.save(path)
    assert path.is_file()
    assert ServerConfig.load(path) == cfg


def test_defaults_applied():
    cfg = ServerConfig(id="abc", name="S", mc_version="1.20.6", loader="vanilla")
    assert cfg.ram_mb == 2048
    assert cfg.port == 25565
    assert cfg.installed_content == []
