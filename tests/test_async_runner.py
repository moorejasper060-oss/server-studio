from server_studio.ui.async_runner import run_sync, AsyncRunner


def test_run_sync_calls_on_done_with_result():
    got = []
    run_sync(lambda: 42, got.append)
    assert got == [42]


def test_run_sync_calls_on_error():
    errs = []
    def boom(): raise RuntimeError("nope")
    run_sync(boom, lambda r: None, errs.append)
    assert "nope" in errs[0]


def test_run_sync_without_on_error_swallows():
    # no on_error provided -> error is swallowed, on_done not called
    done = []
    run_sync((lambda: (_ for _ in ()).throw(ValueError("x"))), done.append)
    assert done == []


def test_async_runner_runs_and_emits(qtbot):
    runner = AsyncRunner()
    got = []
    runner(lambda: 7, got.append)
    qtbot.waitUntil(lambda: got == [7], timeout=2000)


def test_async_runner_two_calls_do_not_crossfire(qtbot):
    runner = AsyncRunner()
    a, b = [], []
    runner(lambda: "A", a.append)
    runner(lambda: "B", b.append)
    qtbot.waitUntil(lambda: a == ["A"] and b == ["B"], timeout=2000)
