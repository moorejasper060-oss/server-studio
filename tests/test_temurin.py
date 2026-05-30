# tests/test_temurin.py
import io
import zipfile
from pathlib import Path
from server_studio.temurin import extract_runtime, resolve_download_url


class FakeResponse:
    def __init__(self, *, json_data=None, content=b""):
        self._json = json_data
        self.content = content

    def json(self):
        return self._json

    def raise_for_status(self):
        return None


class FakeClient:
    def __init__(self, routes):
        self.routes = routes

    def get(self, url, **kwargs):
        return self.routes[url]


def test_resolve_download_url_picks_binary_link():
    api_url = (
        "https://api.adoptium.net/v3/assets/latest/17/hotspot"
        "?architecture=x64&image_type=jdk&os=windows"
    )
    routes = {api_url: FakeResponse(json_data=[
        {"binary": {"package": {"link": "https://example/jdk17.zip"}}},
    ])}
    url = resolve_download_url(FakeClient(routes), major=17, os_name="windows")
    assert url == "https://example/jdk17.zip"


def test_extract_runtime_flattens_single_top_dir(tmp_path):
    # Adoptium archives contain a single top-level dir like "jdk-17.0.11+9";
    # extract_runtime should flatten it so bin/ ends up directly under dest_dir.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("jdk-17.0.11+9/bin/java.exe", "binary")
        zf.writestr("jdk-17.0.11+9/release", "info")
    archive_bytes = buf.getvalue()

    dest_dir = tmp_path / "temurin-17"
    extract_runtime(archive_bytes, dest_dir, suffix=".zip")

    assert (dest_dir / "bin" / "java.exe").is_file()
    assert (dest_dir / "release").is_file()
