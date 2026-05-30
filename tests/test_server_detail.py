# tests/test_server_detail.py
from server_studio.ui.widgets.server_detail import ServerDetail


def _detail(qtbot, running=True):
    d = ServerDetail(server_id="abc", name="SkyBlock SMP", version="1.20.6",
                     loader="fabric", running=running)
    qtbot.addWidget(d)
    return d


def test_has_expected_tabs(qtbot):
    d = _detail(qtbot)
    titles = [d.tabs.tabText(i) for i in range(d.tabs.count())]
    assert titles[:2] == ["Console", "Mods"]
    assert "Settings" in titles and "Sharing" in titles


def test_back_button_emits(qtbot):
    d = _detail(qtbot)
    got = []
    d.back_requested.connect(lambda: got.append(True))
    d.back_btn.click()
    assert got == [True]


def test_console_command_forwarded(qtbot):
    d = _detail(qtbot)
    got = []
    d.command_entered.connect(got.append)
    d.console.input.setText("say hi")
    d.console._submit()
    assert got == ["say hi"]


def test_append_console_line(qtbot):
    d = _detail(qtbot)
    d.append_console_line("Done (4.8s)!")
    assert "Done (4.8s)!" in d.console.log.toPlainText()
