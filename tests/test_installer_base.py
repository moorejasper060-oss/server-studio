# tests/test_installer_base.py
from pathlib import Path
from server_studio.installers.base import InstallResult, Installer
from server_studio.installers.vanilla import VanillaInstaller


def test_install_result_fields():
    r = InstallResult(jar_path=Path("x/server.jar"), java_major=17)
    assert r.jar_path == Path("x/server.jar")
    assert r.java_major == 17


def test_vanilla_installer_satisfies_protocol():
    # VanillaInstaller is constructed with a client; we only check structural typing here.
    assert hasattr(VanillaInstaller, "install")
    # Protocol is runtime_checkable so isinstance works on instances.
    inst = VanillaInstaller(client=object())
    assert isinstance(inst, Installer)
