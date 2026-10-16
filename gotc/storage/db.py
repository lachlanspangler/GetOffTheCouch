"""SQLite access + forward-only migrations.

Why SQLite (ADR-0002): one file, zero ops, transactional, fast enough for millions of rows, trivially
cached/restored in CI. WAL mode so the exporter can read while a fetch writes.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="seconds")


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s)


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path) if str(path) != ":memory:" else path
        if isinstance(self.path, Path):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.migrate()

    def migrate(self) -> list[str]:
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        done = {r[0] for r in self.conn.execute("SELECT name FROM schema_migrations")}
        applied: list[str] = []
        for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if f.name in done:
                continue
            with self.tx():
                for stmt in _split_sql(f.read_text()):
                    self.conn.execute(stmt)
                self.conn.execute(
                    "INSERT INTO schema_migrations(name, applied_at) VALUES (?, ?)", (f.name, iso(utcnow()))
                )
            applied.append(f.name)
        return applied

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        """A transaction. Nested calls join the outer transaction."""
        if self.conn.in_transaction:
            yield self.conn
            return
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise
        else:
            self.conn.execute("COMMIT")

    def execute(self, sql: str, params: tuple[object, ...] | dict[str, object] = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def one(self, sql: str, params: tuple[object, ...] | dict[str, object] = ()) -> sqlite3.Row | None:
        row: sqlite3.Row | None = self.conn.execute(sql, params).fetchone()
        return row

    def all(self, sql: str, params: tuple[object, ...] | dict[str, object] = ()) -> list[sqlite3.Row]:
        return list(self.conn.execute(sql, params).fetchall())

    def close(self) -> None:
        self.conn.close()


def _split_sql(script: str) -> list[str]:
    """Split a migration into statements (our migrations contain no semicolons inside literals)."""
    no_comments = re.sub(r"--[^\n]*", "", script)
    return [s.strip() for s in no_comments.split(";") if s.strip()]
