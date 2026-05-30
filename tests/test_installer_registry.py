# tests/test_installer_registry.py
import pytest
from server_studio.installers.registry import build_installer, SUPPORTED_LOADERS
from server_studio.installers.vanilla import VanillaInstaller
from server_studio.installers.paper import PaperInstaller
from server_studio.installers.purpur import PurpurInstaller
from server_studio.installers.fabric import FabricInstaller


@pytest.mark.parametrize("loader,cls", [
    ("vanilla", VanillaInstaller),
    ("paper", PaperInstaller),
    ("purpur", PurpurInstaller),
    ("fabric", FabricInstaller),
])
def test_build_installer_returns_correct_type(loader, cls):
    inst = build_installer(loader, client=object())
    assert isinstance(inst, cls)


def test_loader_name_is_case_insensitive():
    assert isinstance(build_installer("PAPER", client=object()), PaperInstaller)


def test_unknown_loader_raises():
    with pytest.raises(ValueError):
        build_installer("forge", client=object())


def test_supported_loaders_listed():
    assert set(SUPPORTED_LOADERS) == {"vanilla", "paper", "purpur", "fabric"}
