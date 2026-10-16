"""Incremental builds and exports (SCALING.md §4.6 item 4): skip cities whose inputs didn't change.

A city is rebuilt when any of these changed since its last build (``city_build_state.inputs_hash``):
  * its live ``source_records`` (record ids, content hashes, gone markers)
  * its city config, the global sources file, the taxonomy, its curated venues/registry YAML
  * the caches build_city reads: geocode hits for the city, venue refs, the weather forecast, price snapshots
  * the build code itself (``BUILD_VERSION``; bump it when build/enrich/resolve logic changes)
…or when its last build is older than ``MAX_AGE`` (time-dependent fields: is_new, stale, "past" events), or its
stored events are slim CI placeholders (``data = '{}'``, scripts/slim_state.py), or ``--force-build``.

Exports: a city's card/details files are rewritten only when the feed hash (``generated_at`` excluded) changed
or a file is missing. ``index.json`` and ``health.json`` are always written (they're small and carry ages).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

from gotc.config import CityConfig, Registry
from gotc.settings import CONFIG_DIR
from gotc.storage.db import Database, iso, parse_iso

BUILD_VERSION = "1"
MAX_AGE = timedelta(hours=3)  # the doc suggests 6 h; 3 h keeps `stale` flags at most 3 h late


def _file_hash(h: hashlib._Hash, path: Path) -> None:
    h.update(path.name.encode())
    if path.exists():
        h.update(path.read_bytes())


def inputs_hash(db: Database, reg: Registry, city: CityConfig, config_dir: Path = CONFIG_DIR) -> str:
    h = hashlib.sha256(f"build-v{BUILD_VERSION}".encode())
    h.update(city.model_dump_json().encode())
    h.update(json.dumps(reg.sources_file.model_dump(mode="json"), sort_keys=True).encode())
    for p in (
        config_dir / "taxonomy.yaml",
        config_dir / "venues" / f"{city.slug}.yaml",
        config_dir / "registry" / f"{city.slug}.yaml",
    ):
        _file_hash(h, p)
    reg_dir = config_dir / "registry" / city.slug
    if reg_dir.is_dir():
        for p in sorted(reg_dir.glob("*.yaml")):
            _file_hash(h, p)
    queries = [
        (
            "SELECT unit, record_id, content_hash, gone_at FROM source_records WHERE city = ?"
            " ORDER BY source_id, record_id",
            (city.slug,),
        ),
        ("SELECT COUNT(*), MAX(looked_up_at) FROM geocode_cache WHERE query LIKE ?", (f"{city.slug}|%",)),
        ("SELECT COUNT(*), MAX(fetched_at) FROM venue_refs WHERE city = ?", (city.slug,)),
        ("SELECT fetched_at FROM weather_cache WHERE city = ?", (city.slug,)),
        ("SELECT COUNT(*), MAX(observed_at) FROM price_snapshots WHERE city = ?", (city.slug,)),
    ]
    for sql, params in queries:
        for row in db.conn.execute(sql, params):
            h.update(repr(tuple(row)).encode())
    return h.hexdigest()


def needs_build(db: Database, city: str, h: str, now: datetime) -> tuple[bool, str]:
    row = db.one("SELECT inputs_hash, built_at FROM city_build_state WHERE city = ?", (city,))
    if row is None:
        return True, "never built"
    if row["inputs_hash"] != h:
        return True, "inputs changed"
    built = parse_iso(row["built_at"])
    if built is None or now - built >= MAX_AGE:
        return True, f"last build older than {MAX_AGE.total_seconds() / 3600:.0f} h"
    if db.one("SELECT 1 FROM events WHERE city = ? AND data = '{}' LIMIT 1", (city,)) is not None:
        return True, "slim CI state (events re-derived)"
    return False, "unchanged"


def mark_built(db: Database, city: str, h: str, now: datetime) -> None:
    db.execute(
        "INSERT INTO city_build_state (city, inputs_hash, built_at) VALUES (?,?,?) ON CONFLICT(city) DO UPDATE"
        " SET inputs_hash = excluded.inputs_hash, built_at = excluded.built_at",
        (city, h, iso(now)),
    )


def feed_hash(cards_json: str, details_json: str) -> str:
    """Hash of the exported documents with every ``generated_at`` value blanked."""
    h = hashlib.sha256()
    for doc in (cards_json, details_json):
        data = json.loads(doc)
        data.pop("generated_at", None)
        cov = data.get("coverage")
        if isinstance(cov, dict):
            cov.pop("evaluated_at", None)
        h.update(json.dumps(data, sort_keys=True, separators=(",", ":")).encode())
    return h.hexdigest()


def export_unchanged(db: Database, city: str, fh: str, paths: list[Path]) -> bool:
    row = db.one("SELECT feed_hash FROM city_build_state WHERE city = ?", (city,))
    return bool(row and row["feed_hash"] == fh and all(p.exists() for p in paths))


def mark_exported(db: Database, city: str, fh: str, now: datetime) -> None:
    db.execute(
        "INSERT INTO city_build_state (city, inputs_hash, built_at, feed_hash) VALUES (?, '', ?, ?)"
        " ON CONFLICT(city) DO UPDATE SET feed_hash = excluded.feed_hash",
        (city, iso(now), fh),
    )
