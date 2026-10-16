"""Export: events table → static JSON the dashboard reads (web/public/data/).

  data/index.json              cities, counts, generated_at, schema_version
  data/cities/<slug>.json      CityFeed (validated against gotc.schema.CityFeed before writing)
  data/health.json             per-unit health for the in-app Health page

Writes are atomic (tmp + rename) so the dashboard never reads a half-written file.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from gotc.config import CityConfig, Registry
from gotc.health.store import load_health
from gotc.pipeline.build import venues_for_export
from gotc.schema import SCHEMA_VERSION, CityFeed, Event, NeighborhoodPoint, SourceStatus
from gotc.storage.db import Database, iso
from gotc.taxonomy import taxonomy

HORIZON_DAYS = 180


def _write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data)
    tmp.replace(path)


def source_statuses(db: Database, reg: Registry, city: CityConfig, now: datetime) -> list[SourceStatus]:
    out = []
    for unit in reg.units(city=city.slug):
        h = load_health(db, unit.key)
        sla = reg.sla_hours(unit.source)
        n = db.one(
            "SELECT COUNT(*) c FROM source_records WHERE unit = ? AND gone_at IS NULL AND start_at >= ?",
            (unit.key, iso(now - timedelta(days=1))),
        )
        out.append(
            SourceStatus(
                source_id=unit.source.id,
                name=unit.source.name,
                state=h.state,
                last_success_at=h.last_success_at,
                last_attempt_at=h.last_attempt_at,
                sla_hours=sla,
                stale=h.last_success_at is None or now - h.last_success_at > timedelta(hours=sla),
                records=int(n["c"]) if n else 0,
                last_error=h.last_error,
                reason=h.reason,
            )
        )
    return out


def city_feed(db: Database, reg: Registry, city: CityConfig, now: datetime, include_demo: bool = False) -> CityFeed:
    rows = db.all(
        "SELECT data FROM events WHERE city = ? AND start_at <= ? ORDER BY start_at",
        (city.slug, iso(now + timedelta(days=HORIZON_DAYS))),
    )
    events = [Event.model_validate_json(r["data"]) for r in rows]
    used_venues = {e.venue_id for e in events if e.venue_id}
    return CityFeed(
        generated_at=now,
        city=city.slug,
        city_name=city.name,
        state=city.state,
        timezone=city.timezone,
        center=city.center,
        neighborhoods=[NeighborhoodPoint(name=n.name, lat=n.lat, lon=n.lon) for n in city.neighborhoods],
        events=[e for e in events if include_demo or not e.is_demo],
        is_demo=include_demo,
        venues=[v for v in venues_for_export(db, city.slug) if v.id in used_venues],
        sources=source_statuses(db, reg, city, now),
    )


def export_all(db: Database, reg: Registry, out_dir: Path, now: datetime, include_demo: bool = False) -> dict[str, Any]:
    tax = taxonomy()
    index: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso(now),
        "taxonomy": {
            cid: {"label": c.label, "parent": c.parent, "icon": c.icon}
            for cid, c in tax.categories.items()
            if not c.deprecated
        },
        "tags": tax.tags,
        "cities": [],
    }
    health: dict[str, Any] = {"generated_at": iso(now), "units": []}
    for city in reg.cities.values():
        if not city.enabled:
            continue
        feed = city_feed(db, reg, city, now, include_demo)
        CityFeed.model_validate(feed.model_dump())  # belt and braces: never export an invalid document
        _write(out_dir / "cities" / f"{city.slug}.json", feed.model_dump_json(exclude_none=True))
        upcoming = [e for e in feed.events if e.start >= now - timedelta(hours=3)]
        index["cities"].append(
            {
                "slug": city.slug,
                "name": city.name,
                "state": city.state,
                "timezone": city.timezone,
                "center": list(city.center),
                "events": len(feed.events),
                "upcoming_7d": sum(1 for e in upcoming if e.start <= now + timedelta(days=7)),
                "deadlines": sum(
                    1
                    for e in feed.events
                    if e.registration and e.registration.closes_at and e.registration.closes_at >= now
                ),
                "sources_ok": sum(1 for s in feed.sources if s.state in ("healthy", "recovering")),
                "sources_total": sum(1 for s in feed.sources if s.state != "disabled"),
                "sources_disabled": sum(1 for s in feed.sources if s.state == "disabled"),
                "stale_sources": sum(1 for s in feed.sources if s.stale and s.state != "disabled"),
            }
        )
        for s in feed.sources:
            health["units"].append({"city": city.slug, **json.loads(s.model_dump_json())})
    _write(out_dir / "index.json", json.dumps(index, separators=(",", ":")))
    log_rows = db.all("SELECT at, unit, level, kind, message FROM health_log ORDER BY id DESC LIMIT 200")
    health["log"] = [dict(r) for r in log_rows]
    _write(out_dir / "health.json", json.dumps(health, separators=(",", ":")))
    return index
