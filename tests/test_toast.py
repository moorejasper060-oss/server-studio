from server_studio.ui.widgets.toast import Toast


def test_show_message_sets_text_and_shows(qtbot):
    t = Toast(); qtbot.addWidget(t)
    t.show_message("Something failed", duration_ms=50)
    assert t.text() == "Something failed"
    assert t.isVisible()


def test_show_message_replaces_text(qtbot):
    t = Toast(); qtbot.addWidget(t)
    t.show_message("first", duration_ms=50)
    t.show_message("second", duration_ms=50)
    assert t.text() == "second"
