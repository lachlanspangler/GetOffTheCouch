"""Raw payload store: every parsed HTTP body is kept gzipped, content-addressed, for replay and debugging.

Layout: data/raw/<source_id>/<YYYY-MM-DD>/<sha256[:20]>.<ext>.gz — identical bodies are stored once.
``gotc replay`` re-parses stored payloads after a parser fix, without touching the network.
"""

from __future__ import annotations

import gzip
import hashlib
from datetime import datetime
from pathlib import Path


class RawStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def put(self, source_id: str, fetched_at: datetime, content: bytes, ext: str) -> tuple[str, str]:
        digest = hashlib.sha256(content).hexdigest()
        rel = Path(source_id) / fetched_at.strftime("%Y-%m-%d") / f"{digest[:20]}.{ext}.gz"
        path = self.root / rel
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            with gzip.open(tmp, "wb", compresslevel=6) as fh:
                fh.write(content)
            tmp.replace(path)  # atomic: a crash never leaves a half-written payload
        return digest, rel.as_posix()

    def get(self, rel: str) -> bytes:
        with gzip.open(self.root / rel, "rb") as fh:
            return fh.read()

    def exists(self, rel: str) -> bool:
        return (self.root / rel).exists()
