# tests/test_new_server_wizard.py
from server_studio.ui.widgets.new_server_wizard import NewServerWizard


def test_starts_on_version_step(qtbot):
    w = NewServerWizard(versions=["1.21", "1.20.6"])
    qtbot.addWidget(w)
    assert w.stack.currentIndex() == 0


def test_full_flow_collects_values(qtbot):
    w = NewServerWizard(versions=["1.21", "1.20.6"])
    qtbot.addWidget(w)
    w.select_version("1.20.6")
    w.next_step()                      # -> loader
    assert w.stack.currentIndex() == 1
    w.select_loader("fabric")
    w.next_step()                      # -> configure
    assert w.stack.currentIndex() == 2
    w.name_input.setText("My SMP")
    w.ram_slider.setValue(4096)
    data = w.result_data
    assert data == {"name": "My SMP", "mc_version": "1.20.6",
                    "loader": "fabric", "ram_mb": 4096}


def test_loader_step_lists_supported_loaders(qtbot):
    w = NewServerWizard(versions=["1.20.6"])
    qtbot.addWidget(w)
    w.select_version("1.20.6")
    w.next_step()
    assert set(w.loader_buttons) == {"vanilla", "paper", "purpur", "fabric"}


def test_back_step_returns(qtbot):
    w = NewServerWizard(versions=["1.20.6"])
    qtbot.addWidget(w)
    w.select_version("1.20.6")
    w.next_step()
    w.back_step()
    assert w.stack.currentIndex() == 0
