"""Paths and environment. Secrets come only from the environment (or a gitignored .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = Path(os.environ.get("GOTC_DATA_DIR", ROOT / "data"))
WEB_DATA_DIR = Path(os.environ.get("GOTC_WEB_DATA_DIR", ROOT / "web" / "public" / "data"))
DOCS_DIR = ROOT / "docs"

USER_AGENT = os.environ.get(
    "GOTC_USER_AGENT",
    "GetOffTheCouch/0.1 (+https://github.com/lachlanspangler/GetOffTheCouch; events dashboard for newcomers)",
)


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env loader (KEY=VALUE lines). Existing environment variables win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    data_dir: Path = DATA_DIR
    web_data_dir: Path = WEB_DATA_DIR
    config_dir: Path = CONFIG_DIR
    docs_dir: Path = DOCS_DIR
    user_agent: str = USER_AGENT
    offline: bool = field(default_factory=lambda: os.environ.get("GOTC_OFFLINE") == "1")

    @property
    def db_path(self) -> Path:
        return self.data_dir / "gotc.db"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def http_cache_dir(self) -> Path:
        return self.data_dir / "http_cache"

    @staticmethod
    def secret(name: str) -> str | None:
        value = os.environ.get(name, "").strip()
        return value or None
