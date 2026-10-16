"""Shard deltas for the sharded CI refresh (SCALING.md §4.6 item 3, ADR-0008).

Every shard job restores the same pipeline-state DB, records ``mark`` (max ids + time), fetches only its
cities' units (``gotc run --cities … --no-build``) and exports a **delta DB** with what it changed:

  runs / run_units          new runs (ids remapped on merge)
  raw_fetches / rejects     new rows (ids remapped; source_records.raw_fetch_id follows)
  health_log                new rows
  source_records            every row of the shard's cities (replaces the publish DB's rows for those cities)
  unit_health               every row of the shard's cities
  price_snapshots           rows observed since the mark

The publish job merges every delta into its own copy of the same base DB, then builds and exports once.
Cities are disjoint across shards, so no two deltas touch the same rows. A delta whose base doesn't match the
publish DB (a different state commit) is refused rather than merged into the wrong history.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from gotc.storage.db import Database, iso, utcnow

ID_TABLES = ("runs", "raw_fetches", "rejects", "health_log")


class DeltaMismatch(Exception):
    pass


def mark(db: Database, now: datetime | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {t: int(db.one(f"SELECT COALESCE(MAX(id), 0) m FROM {t}")["m"]) for t in ID_TABLES}  # type: ignore[index]
    out["at"] = iso(now or utcnow())
    return out


def _like(cities: list[str]) -> str:
    return " OR ".join(f"unit LIKE '%@{c}'" for c in cities) or "0"


def _in(cities: list[str]) -> str:
    return "(" + ",".join(f"'{c}'" for c in cities) + ")" if cities else "('')"


def _check_slugs(cities: list[str]) -> None:
    for c in cities:
        if not c.replace("_", "").isalnum() or c.lower() != c:
            raise ValueError(f"bad city slug {c!r}")


def export_delta(db_path: Path, base: dict[str, Any], cities: list[str], out: Path) -> dict[str, int]:
    """Write the shard's changes since ``base`` to ``out`` (a fresh SQLite file with the same schema)."""
    _check_slugs(cities)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    Database(out).close()  # create the schema via the migrations
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = OFF")
    con.execute("ATTACH DATABASE ? AS d", (str(out),))
    q = {
        "runs": f"SELECT * FROM runs WHERE id > {int(base['runs'])}",
        "run_units": f"SELECT * FROM run_units WHERE run_id > {int(base['runs'])} AND ({_like(cities)})",
        "raw_fetches": f"SELECT * FROM raw_fetches WHERE id > {int(base['raw_fetches'])} AND city IN {_in(cities)}",
        "rejects": f"SELECT * FROM rejects WHERE id > {int(base['rejects'])} AND ({_like(cities)})",
        "health_log": f"SELECT * FROM health_log WHERE id > {int(base['health_log'])} AND ({_like(cities)})",
        "source_records": f"SELECT * FROM source_records WHERE city IN {_in(cities)}",
        "unit_health": f"SELECT * FROM unit_health WHERE city IN {_in(cities)}",
        "price_snapshots": f"SELECT * FROM price_snapshots WHERE city IN {_in(cities)} AND observed_at >= ?",
    }
    counts: dict[str, int] = {}
    with con:
        for table, sql in q.items():
            params: tuple[Any, ...] = (base["at"],) if "?" in sql else ()
            cur = con.execute(f"INSERT INTO d.{table} {sql}", params)
            counts[table] = cur.rowcount
        con.execute("CREATE TABLE d.delta_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        con.execute(
            "INSERT INTO d.delta_meta VALUES ('base', ?), ('cities', ?)", (json.dumps(base), json.dumps(cities))
        )
    con.execute("DETACH DATABASE d")
    con.close()
    return counts


def merge_delta(db: Database, delta: Path, expect_base: dict[str, Any]) -> dict[str, int]:
    """Merge one shard delta into ``db`` (the publish job's copy of the same base state)."""
    con = db.conn
    con.execute("ATTACH DATABASE ? AS d", (str(delta),))
    try:
        meta = {r[0]: json.loads(r[1]) for r in con.execute("SELECT key, value FROM d.delta_meta")}
        base, cities = meta["base"], list(meta["cities"])
        _check_slugs(cities)
        if any(int(base[t]) != int(expect_base[t]) for t in ID_TABLES):
            raise DeltaMismatch(f"{delta.name}: base {base} != publish DB {expect_base} (different state commit?)")
        counts: dict[str, int] = {}
        con.execute("PRAGMA foreign_keys = OFF")
        with db.tx():
            run_map: dict[int, int] = {}
            for r in con.execute("SELECT * FROM d.runs ORDER BY id").fetchall():
                cur = con.execute(
                    "INSERT INTO runs (started_at, finished_at, status, trigger, summary) VALUES (?,?,?,?,?)",
                    (r["started_at"], r["finished_at"], r["status"], r["trigger"], r["summary"]),
                )
                run_map[int(r["id"])] = int(cur.lastrowid or 0)
            counts["runs"] = len(run_map)
            n = 0
            for r in con.execute("SELECT * FROM d.run_units").fetchall():
                row = dict(r)
                row["run_id"] = run_map.get(int(row["run_id"]), row["run_id"])
                _insert(con, "run_units", row, replace=True)
                n += 1
            counts["run_units"] = n
            raw_map: dict[int, int] = {}
            for r in con.execute("SELECT * FROM d.raw_fetches ORDER BY id").fetchall():
                row = dict(r)
                old = int(row.pop("id"))
                if row["run_id"] is not None:
                    row["run_id"] = run_map.get(int(row["run_id"]), row["run_id"])
                raw_map[old] = _insert(con, "raw_fetches", row)
            counts["raw_fetches"] = len(raw_map)

            def remap(v: Any) -> Any:
                return raw_map.get(int(v), v) if v is not None else None

            n = 0
            for r in con.execute("SELECT * FROM d.rejects ORDER BY id").fetchall():
                row = dict(r)
                row.pop("id")
                row["raw_fetch_id"] = remap(row["raw_fetch_id"])
                _insert(con, "rejects", row)
                n += 1
            counts["rejects"] = n
            n = 0
            for r in con.execute("SELECT * FROM d.health_log ORDER BY id").fetchall():
                row = dict(r)
                row.pop("id")
                _insert(con, "health_log", row)
                n += 1
            counts["health_log"] = n
            con.execute(f"DELETE FROM source_records WHERE city IN {_in(cities)}")
            n = 0
            for r in con.execute("SELECT * FROM d.source_records").fetchall():
                row = dict(r)
                row["raw_fetch_id"] = remap(row["raw_fetch_id"])
                _insert(con, "source_records", row)
                n += 1
            counts["source_records"] = n
            for table in ("unit_health", "price_snapshots"):
                cols = [c[1] for c in con.execute(f"PRAGMA d.table_info({table})")]
                cur = con.execute(
                    f"INSERT OR REPLACE INTO main.{table} ({','.join(cols)}) SELECT {','.join(cols)} FROM d.{table}"
                )
                counts[table] = cur.rowcount
    finally:
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("DETACH DATABASE d")
    return counts


def _insert(con: sqlite3.Connection, table: str, row: dict[str, Any], replace: bool = False) -> int:
    cols = list(row)
    verb = "INSERT OR REPLACE" if replace else "INSERT"
    cur = con.execute(
        f"{verb} INTO main.{table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", tuple(row.values())
    )
    return int(cur.lastrowid or 0)


def plan_shards(units_by_city: dict[str, int], size: int) -> list[list[str]]:
    """Pack cities into ceil(n/size) shards, balanced by unit count (largest first, greedy)."""
    if not units_by_city:
        return []
    n = max(1, -(-len(units_by_city) // max(1, size)))
    shards: list[list[str]] = [[] for _ in range(n)]
    load = [0] * n
    for city, units in sorted(units_by_city.items(), key=lambda kv: (-kv[1], kv[0])):
        i = load.index(min(load))
        shards[i].append(city)
        load[i] += units
    return [sorted(s) for s in shards if s]
