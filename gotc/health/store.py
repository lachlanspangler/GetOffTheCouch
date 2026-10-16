"""Persist unit health and the append-only health log."""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime
from typing import Any

from gotc.config import Unit
from gotc.health.state import Health
from gotc.storage.db import Database, iso, parse_iso

_DT_FIELDS = {"last_attempt_at", "last_success_at", "last_failure_at", "next_due_at"}


def load_health(db: Database, unit_key: str) -> Health:
    row = db.one("SELECT * FROM unit_health WHERE unit = ?", (unit_key,))
    if row is None:
        return Health()
    kw: dict[str, Any] = {}
    for f in fields(Health):
        v = row[f.name]
        kw[f.name] = parse_iso(v) if f.name in _DT_FIELDS else v
    return Health(**kw)


def save_health(db: Database, unit: Unit, h: Health) -> None:
    vals = {f.name: getattr(h, f.name) for f in fields(Health)}
    for k in _DT_FIELDS:
        vals[k] = iso(vals[k]) if vals[k] else None
    cols = ", ".join(["unit", "source_id", "city", *vals])
    qs = ", ".join("?" * (3 + len(vals)))
    updates = ", ".join(f"{k}=excluded.{k}" for k in vals)
    db.execute(
        f"INSERT INTO unit_health ({cols}) VALUES ({qs}) ON CONFLICT(unit) DO UPDATE SET {updates}",
        (unit.key, unit.source.id, unit.city.slug, *vals.values()),
    )


def get_cursor(db: Database, unit_key: str) -> str | None:
    row = db.one("SELECT cursor FROM unit_health WHERE unit = ?", (unit_key,))
    return row["cursor"] if row else None


def set_cursor(db: Database, unit_key: str, cursor: str) -> None:
    db.execute("UPDATE unit_health SET cursor = ? WHERE unit = ?", (cursor, unit_key))


def log(db: Database, unit_key: str, level: str, kind: str, message: str, at: datetime) -> None:
    db.execute(
        "INSERT INTO health_log (at, unit, level, kind, message) VALUES (?, ?, ?, ?, ?)",
        (iso(at), unit_key, level, kind, message[:1000]),
    )
