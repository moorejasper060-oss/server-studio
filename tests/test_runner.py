# tests/test_runner.py
import sys
from server_studio.installers.runner import run_process


def test_run_process_succeeds(tmp_path):
    run_process([sys.executable, "-c", "open('ok.txt','w').write('hi')"], cwd=tmp_path)
    assert (tmp_path / "ok.txt").read_text() == "hi"


def test_run_process_raises_on_nonzero(tmp_path):
    try:
        run_process([sys.executable, "-c", "import sys; sys.exit(3)"], cwd=tmp_path)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "3" in str(exc)
