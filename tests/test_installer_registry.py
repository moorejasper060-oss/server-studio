# tests/test_installer_registry.py
import pytest
from server_studio.installers.registry import build_installer, SUPPORTED_LOADERS
from server_studio.installers.vanilla import VanillaInstaller
from server_studio.installers.paper import PaperInstaller
from server_studio.installers.purpur import PurpurInstaller
from server_studio.installers.fabric import FabricInstaller
from server_studio.installers.forge import ForgeInstaller
from server_studio.installers.neoforge import NeoForgeInstaller
from server_studio.installers.spigot import SpigotInstaller

_J = lambda major: "/java"
_R = lambda command, cwd: None


@pytest.mark.parametrize("loader,cls", [
    ("vanilla", VanillaInstaller),
    ("paper", PaperInstaller),
    ("purpur", PurpurInstaller),
    ("fabric", FabricInstaller),
    ("forge", ForgeInstaller),
    ("neoforge", NeoForgeInstaller),
    ("spigot", SpigotInstaller),
])
def test_build_installer_returns_correct_type(loader, cls):
    inst = build_installer(loader, client=object(), java_resolver=_J, runner=_R)
    assert isinstance(inst, cls)


def test_simple_loader_without_java_or_runner_still_builds():
    assert isinstance(build_installer("paper", client=object()), PaperInstaller)


def test_process_loader_requires_java_and_runner():
    with pytest.raises(ValueError):
        build_installer("forge", client=object())


def test_unknown_loader_raises():
    with pytest.raises(ValueError):
        build_installer("bogus", client=object(), java_resolver=_J, runner=_R)


def test_supported_loaders_listed():
    assert set(SUPPORTED_LOADERS) == {
        "vanilla", "paper", "purpur", "fabric", "forge", "neoforge", "spigot",
    }
