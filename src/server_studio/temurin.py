# src/server_studio/temurin.py
from __future__ import annotations

import io
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ADOPTIUM = "https://api.adoptium.net/v3/assets/latest/{major}/hotspot"


def _os_name() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def resolve_download_url(client, major: int, os_name: str | None = None) -> str:
    os_name = os_name or _os_name()
    base = ADOPTIUM.format(major=major)
    full_url = f"{base}?architecture=x64&image_type=jdk&os={os_name}"
    resp = client.get(full_url)
    resp.raise_for_status()
    assets = resp.json()
    if not assets:
        raise RuntimeError(f"No Temurin {major} build for os={os_name}")
    return assets[0]["binary"]["package"]["link"]


def extract_runtime(archive_bytes: bytes, dest_dir: Path, suffix: str) -> None:
    """Extract a Temurin archive into dest_dir, flattening the single top-level dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as staging_str:
        staging = Path(staging_str)
        if suffix == ".zip":
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
                zf.extractall(staging)
        else:  # .tar.gz
            with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tf:
                tf.extractall(staging)

        tops = [p for p in staging.iterdir()]
        root = tops[0] if len(tops) == 1 and tops[0].is_dir() else staging
        for item in root.iterdir():
            target = dest_dir / item.name
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                for sub in item.rglob("*"):
                    rel = sub.relative_to(item)
                    out = target / rel
                    if sub.is_dir():
                        out.mkdir(parents=True, exist_ok=True)
                    else:
                        out.parent.mkdir(parents=True, exist_ok=True)
                        out.write_bytes(sub.read_bytes())
            else:
                target.write_bytes(item.read_bytes())


def temurin_fetcher(client):
    """Return a fetcher(major, dest_dir) that downloads + extracts Temurin."""
    def fetch(major: int, dest_dir: Path) -> None:
        url = resolve_download_url(client, major)
        suffix = ".zip" if url.endswith(".zip") else ".tar.gz"
        resp = client.get(url)
        resp.raise_for_status()
        extract_runtime(resp.content, dest_dir, suffix=suffix)
    return fetch
