import sys
import time
from server_studio.process import ServerProcess


# A tiny program that prints "ready", then echoes each stdin line as "echo: <line>".
CHILD_SCRIPT = (
    "import sys\n"
    "print('ready', flush=True)\n"
    "for line in sys.stdin:\n"
    "    sys.stdout.write('echo: ' + line)\n"
    "    sys.stdout.flush()\n"
)


def _wait_for(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_streams_output_and_echoes_commands(tmp_path):
    lines = []
    proc = ServerProcess(
        command=[sys.executable, "-c", CHILD_SCRIPT],
        cwd=tmp_path,
        on_output=lines.append,
    )
    proc.start()
    assert _wait_for(lambda: "ready" in lines)

    proc.send("hello")
    assert _wait_for(lambda: any("echo: hello" in line for line in lines))

    proc.stop(timeout=1.0)
    assert _wait_for(lambda: not proc.is_running())


def test_is_running_false_before_start(tmp_path):
    proc = ServerProcess(command=[sys.executable, "-c", "pass"], cwd=tmp_path,
                         on_output=lambda _l: None)
    assert proc.is_running() is False


def test_stop_after_process_already_exited(tmp_path):
    proc = ServerProcess(command=[sys.executable, "-c", "pass"], cwd=tmp_path,
                         on_output=lambda _l: None)
    proc.start()
    assert _wait_for(lambda: not proc.is_running())  # trivial child exits immediately
    proc.stop()  # must NOT raise even though the process is already gone
    assert proc.is_running() is False
