# tests/test_java_versions.py
import pytest
from server_studio.java_versions import java_major_for_version


@pytest.mark.parametrize("version,expected", [
    ("1.8.9", 8),
    ("1.12.2", 8),
    ("1.16.5", 8),
    ("1.17", 17),
    ("1.17.1", 17),
    ("1.18.2", 17),
    ("1.19.4", 17),
    ("1.20", 17),
    ("1.20.4", 17),
    ("1.20.5", 21),
    ("1.20.6", 21),
    ("1.21", 21),
    ("1.21.4", 21),
])
def test_known_versions_map_to_expected_java(version, expected):
    assert java_major_for_version(version) == expected


def test_unparseable_version_defaults_to_21():
    assert java_major_for_version("garbage") == 21
    assert java_major_for_version("24w14a") == 21  # snapshot → default latest
