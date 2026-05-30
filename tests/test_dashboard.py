# tests/test_dashboard.py
from server_studio.ui.widgets.dashboard import Dashboard


class Cfg:
    def __init__(self, id, name, mc_version, loader):
        self.id, self.name, self.mc_version, self.loader = id, name, mc_version, loader


def test_empty_state_when_no_servers(qtbot):
    d = Dashboard()
    qtbot.addWidget(d)
    d.set_servers([], running_ids=set())
    assert d.empty_label.isVisible()
    assert d.card_count() == 0


def test_renders_one_card_per_server(qtbot):
    d = Dashboard()
    qtbot.addWidget(d)
    d.set_servers([Cfg("a", "A", "1.20.6", "paper"), Cfg("b", "B", "1.21", "fabric")],
                  running_ids={"a"})
    assert d.card_count() == 2
    assert not d.empty_label.isVisible()


def test_new_button_emits(qtbot):
    d = Dashboard()
    qtbot.addWidget(d)
    got = []
    d.new_requested.connect(lambda: got.append(True))
    d.new_btn.click()
    assert got == [True]


def test_open_request_bubbles_up_with_id(qtbot):
    d = Dashboard()
    qtbot.addWidget(d)
    d.set_servers([Cfg("a", "A", "1.20.6", "paper")], running_ids=set())
    got = []
    d.open_requested.connect(got.append)
    d._cards["a"].open_btn.click()
    assert got == ["a"]
