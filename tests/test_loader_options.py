# tests/test_loader_options.py
from server_studio.ui.loader_options import loader_options_for_version
from server_studio.installers.registry import SUPPORTED_LOADERS


def test_returns_one_option_per_supported_loader():
    opts = loader_options_for_version("1.20.6")
    keys = [o.key for o in opts]
    assert set(keys) == set(SUPPORTED_LOADERS)


def test_options_have_label_and_kind():
    opts = loader_options_for_version("1.20.6")
    by_key = {o.key: o for o in opts}
    assert by_key["vanilla"].kind == "none"
    assert by_key["paper"].kind == "plugins"
    assert by_key["fabric"].kind == "mods"
    assert by_key["forge"].kind == "mods"
    assert by_key["neoforge"].kind == "mods"
    assert by_key["spigot"].kind == "plugins"
    for o in opts:
        assert o.label
