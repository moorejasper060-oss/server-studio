# tests/test_console_view.py
from server_studio.ui.widgets.console_view import ConsoleView


def test_append_line_shows_in_log(qtbot):
    w = ConsoleView()
    qtbot.addWidget(w)
    w.append_line("Done (4.8s)! For help, type help")
    assert "Done (4.8s)!" in w.log.toPlainText()


def test_command_input_emits_signal_and_clears(qtbot):
    w = ConsoleView()
    qtbot.addWidget(w)
    received = []
    w.command_entered.connect(received.append)
    w.input.setText("weather clear")
    with qtbot.waitSignal(w.command_entered, timeout=500):
        w._submit()
    assert received == ["weather clear"]
    assert w.input.text() == ""


def test_blank_command_is_ignored(qtbot):
    w = ConsoleView()
    qtbot.addWidget(w)
    received = []
    w.command_entered.connect(received.append)
    w.input.setText("   ")
    w._submit()
    assert received == []
