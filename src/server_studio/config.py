from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class ServerConfig:
    """Serialized as server.json inside a server's directory."""

    id: str
    name: str
    mc_version: str
    loader: str
    loader_version: str | None = None
    java_runtime: str | None = None
    ram_mb: int = 2048
    port: int = 25565
    installed_content: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ServerConfig":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ServerConfig":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
