import pytest
from server_studio.installers.content_target import content_dir_name, supports_content


@pytest.mark.parametrize("loader,expected", [
    ("fabric", "mods"), ("forge", "mods"), ("neoforge", "mods"),
    ("paper", "plugins"), ("purpur", "plugins"), ("spigot", "plugins"),
])
def test_content_dir(loader, expected):
    assert content_dir_name(loader) == expected


def test_vanilla_has_no_content_dir():
    assert content_dir_name("vanilla") is None
    assert supports_content("vanilla") is False
    assert supports_content("fabric") is True
