# tests/test_launch_detect.py
from server_studio.installers.launch_detect import detect_launch_args


def test_modern_args_file(tmp_path):
    args = tmp_path / "libraries" / "net" / "minecraftforge" / "forge" / "1.20.6-50.0.0"
    args.mkdir(parents=True)
    (args / "win_args.txt").write_text("@stuff", encoding="utf-8")
    result = detect_launch_args(tmp_path)
    assert result == [
        "@libraries/net/minecraftforge/forge/1.20.6-50.0.0/win_args.txt", "nogui",
    ]


def test_legacy_runnable_jar(tmp_path):
    (tmp_path / "forge-1.12.2-14.23.5.2860-universal.jar").write_text("", encoding="utf-8")
    (tmp_path / "forge-1.12.2-14.23.5.2860-installer.jar").write_text("", encoding="utf-8")
    result = detect_launch_args(tmp_path)
    assert result == ["-jar", "forge-1.12.2-14.23.5.2860-universal.jar", "nogui"]


def test_fallback_to_server_jar(tmp_path):
    assert detect_launch_args(tmp_path) == ["-jar", "server.jar", "nogui"]


def test_neoforge_legacy_runnable_jar(tmp_path):
    (tmp_path / "neoforge-20.4.190-universal.jar").write_text("", encoding="utf-8")
    (tmp_path / "neoforge-20.4.190-installer.jar").write_text("", encoding="utf-8")
    assert detect_launch_args(tmp_path) == [
        "-jar", "neoforge-20.4.190-universal.jar", "nogui",
    ]


def test_args_file_takes_priority_over_legacy_jar(tmp_path):
    args = tmp_path / "libraries" / "net" / "neoforged" / "neoforge" / "20.6.119"
    args.mkdir(parents=True)
    (args / "win_args.txt").write_text("@x", encoding="utf-8")
    (tmp_path / "forge-1.20.6-50.0.0-universal.jar").write_text("", encoding="utf-8")
    assert detect_launch_args(tmp_path) == [
        "@libraries/net/neoforged/neoforge/20.6.119/win_args.txt", "nogui",
    ]
