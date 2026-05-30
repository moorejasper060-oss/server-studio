# tests/test_ui_imports.py
def test_pyside6_and_ui_package_import():
    import PySide6  # noqa: F401
    import server_studio.ui  # noqa: F401
    assert server_studio.ui.__doc__ is not None
