# tests/test_java_manager.py
import sys
from pathlib import Path
import pytest
from server_studio.paths import AppPaths
from server_studio.java_manager import JavaManager


def _java_exe_name():
    return "java.exe" if sys.platform == "win32" else "java"


def test_resolve_returns_cached_runtime_without_fetching(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()
    # Pre-seed a cached runtime for Java 17.
    runtime = paths.java / "temurin-17" / "bin"
    runtime.mkdir(parents=True)
    exe = runtime / _java_exe_name()
    exe.write_text("", encoding="utf-8")

    fetch_calls = []

    def fetcher(major, dest_dir):
        fetch_calls.append((major, dest_dir))

    mgr = JavaManager(paths=paths, fetcher=fetcher)
    result = mgr.resolve(17)

    assert result == exe
    assert fetch_calls == []  # already cached → no download


def test_resolve_invokes_fetcher_when_missing(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()

    def fetcher(major, dest_dir):
        # Simulate a successful download+extract by creating the executable.
        bin_dir = Path(dest_dir) / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        (bin_dir / _java_exe_name()).write_text("", encoding="utf-8")

    mgr = JavaManager(paths=paths, fetcher=fetcher)
    result = mgr.resolve(21)

    assert result == paths.java / "temurin-21" / "bin" / _java_exe_name()
    assert result.is_file()


def test_resolve_raises_if_fetcher_does_not_produce_executable(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()

    def fetcher(major, dest_dir):
        pass  # produces nothing

    mgr = JavaManager(paths=paths, fetcher=fetcher)
    with pytest.raises(RuntimeError):
        mgr.resolve(21)


def test_resolver_is_callable_matching_signature(tmp_path):
    paths = AppPaths(root=tmp_path)
    paths.ensure()
    runtime = paths.java / "temurin-8" / "bin"
    runtime.mkdir(parents=True)
    (runtime / _java_exe_name()).write_text("", encoding="utf-8")

    mgr = JavaManager(paths=paths, fetcher=lambda m, d: None)
    resolver = mgr.resolver
    assert callable(resolver)
    assert resolver(8) == runtime / _java_exe_name()
