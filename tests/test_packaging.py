import importlib.util
from pathlib import Path


def test_entry_module_exposes_main():
    """The PyInstaller entry script imports cleanly and exposes a callable `main`."""
    from server_studio.ui.main import main
    assert callable(main)

    entry = Path(__file__).resolve().parents[1] / "packaging" / "entry.py"
    assert entry.is_file()

    spec = importlib.util.spec_from_file_location("ss_entry", entry)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # __name__ != "__main__", so main() is not invoked
    assert callable(module.main)


def test_spec_and_build_script_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "server-studio.spec").is_file()
    assert (root / "scripts" / "build.ps1").is_file()
