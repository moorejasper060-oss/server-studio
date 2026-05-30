# tests/test_content_service.py
from server_studio.ui.content_service import ContentService


class FakeSearch:
    def search(self, query, mc_version, loader):
        return [type("R", (), {"project_id": "A", "title": "Sodium",
                               "description": "perf", "slug": "sodium"})()]
    def get_files(self, project_id, mc_version, loader):
        return [type("F", (), {"version_id": "v1", "filename": "sodium.jar",
                               "url": "https://cdn/s.jar"})()]


class FakeContent:
    def __init__(self):
        self.installed = []
    def install(self, server_id, *, source, project_id, version_id, filename, url):
        self.installed.append(filename)
    def list_installed(self, server_id):
        return [{"filename": f, "enabled": True} for f in self.installed]
    def set_enabled(self, server_id, filename, enabled): pass
    def remove(self, server_id, filename): pass


def test_service_search_and_install():
    svc = ContentService(server_id="s1", mc_version="1.20.6", loader="fabric",
                         search_client=FakeSearch(), content=FakeContent())
    results = svc.search("sodium")
    assert results[0]["title"] == "Sodium"
    svc.install(results[0])
    assert svc.list_installed()[0]["filename"] == "sodium.jar"
