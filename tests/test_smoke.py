import server_studio


def test_package_has_version():
    assert isinstance(server_studio.__version__, str)
