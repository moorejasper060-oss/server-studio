from server_studio.installers.version_list import list_release_versions, DEFAULT_VERSIONS


class FakeResp:
    def __init__(self, j): self._j = j
    def json(self): return self._j
    def raise_for_status(self): return None


class FakeClient:
    def __init__(self, j): self._j = j
    def get(self, url): return FakeResp(self._j)


def test_filters_to_releases_newest_first():
    data = {"versions": [
        {"id": "1.20.6", "type": "release"},
        {"id": "24w14a", "type": "snapshot"},
        {"id": "1.20.4", "type": "release"},
    ]}
    assert list_release_versions(FakeClient(data)) == ["1.20.6", "1.20.4"]


def test_default_versions_nonempty():
    assert DEFAULT_VERSIONS and all(isinstance(v, str) for v in DEFAULT_VERSIONS)
