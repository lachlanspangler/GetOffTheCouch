"""Export: events table → static JSON the dashboard reads (web/public/data/).

  data/index.json              cities, counts, generated_at, schema_version
  data/cities/<slug>.json      CityFeed (validated against gotc.schema.CityFeed before writing)
  data/cities/<slug>.details.json  CityDetails: provenance + full summaries, loaded when a card opens
  data/cities/<slug>/manifest.json CityManifest: the same cards split into week shards (I-117)
    meta.<hash>.json  w/<key>.<hash>.json  d/<key>.<hash>.json
  data/health.json             per-unit health for the in-app Health page

Writes are atomic (tmp + rename) so the dashboard never reads a half-written file.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from gotc.config import CityConfig, Registry
from gotc.health.reliability import reliability
from gotc.health.store import load_health
from gotc.pipeline.build import venues_for_export
from gotc.pipeline.gate import gate_city
from gotc.pipeline.incremental import export_unchanged, feed_hash, mark_exported
from gotc.pipeline.rankprep import annotate
from gotc.pipeline.starter_pack import load as load_starter_pack
from gotc.pipeline.starter_pack import with_status
from gotc.schema import (
    SCHEMA_VERSION,
    CityDetails,
    CityFeed,
    CityManifest,
    CityShard,
    CityShardDetails,
    Event,
    EventDetail,
    EventKind,
    Method,
    NeighborhoodPoint,
    ShardFile,
    ShardKind,
    ShardRef,
    SourceStatus,
)
from gotc.storage.db import Database, iso
from gotc.taxonomy import taxonomy

log = logging.getLogger(__name__)
HORIZON_DAYS = 180
PLAN_AHEAD_DAYS = 400  # cons, faires and league seasons are planned months ahead


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
            (unit.key, iso(now - timedelta(days=60))),
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
        "SELECT data FROM events WHERE city = ? AND (start_at <= ? OR (start_at <= ? AND (category LIKE 'niche.%'"
        " OR category LIKE 'sports_league.%'))) ORDER BY start_at",
        (city.slug, iso(now + timedelta(days=HORIZON_DAYS)), iso(now + timedelta(days=PLAN_AHEAD_DAYS))),
    )
    events: list[Event] = []
    bad = 0
    for r in rows:
        try:
            events.append(Event.model_validate_json(r["data"]))
        except ValueError:
            bad += 1  # e.g. slimmed CI state for a city whose rebuild failed: skip, never crash every city
    if bad:
        log.warning("%s: skipped %d unreadable event rows", city.slug, bad)
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
        starter_pack=with_status(db, load_starter_pack(city.state)),
    )


CARD_SUMMARY_CHARS = 240


def split_feed(feed: CityFeed) -> tuple[CityFeed, CityDetails]:
    """Cards keep what lists/filters/maps need; provenance + full summaries go to the lazy details file."""
    details: dict[str, EventDetail] = {}
    cards = []
    for e in feed.events:
        details[e.id] = EventDetail(summary=e.summary, provenance=e.provenance)
        short = e.summary
        if short and len(short) > CARD_SUMMARY_CHARS:
            short = short[: CARD_SUMMARY_CHARS - 1].rsplit(" ", 1)[0] + "…"
        cards.append(e.model_copy(update={"provenance": {}, "summary": short}))
    return (
        feed.model_copy(update={"events": cards}),
        CityDetails(generated_at=feed.generated_at, city=feed.city, events=details),
    )


SHARD_WEEKS = 12  # weekly shards for the current week and this many after it; the rest share `later`
HASH_CHARS = 10
SHARD_EVENTS = 400  # a busy week splits into parts of at most this many cards (≈ 100 KB gzip, budget 150)
SHARD_VERSION = 3  # bump when shard_of() changes, so unchanged feeds are re-sharded on the next export


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _has_deadline(e: Event, now: datetime) -> bool:
    r = e.registration
    if r is None:
        return False
    return any(t is not None and t >= now for t in (r.closes_at, r.opens_at, r.early_bird_ends_at))


def shard_of(e: Event, tz: ZoneInfo, week0: date, now: datetime) -> tuple[str, ShardKind, date | None]:
    """Which shard a card lives in (see CityManifest). ``week0`` is the Monday of the export's current week."""
    if e.kind == EventKind.OPENING:  # license signals: the start is a filing date, not when to go
        return "openings", "openings", None
    monday = _monday(e.start.astimezone(tz).date())
    if monday < week0:
        if (e.end or e.start + timedelta(hours=3)) < now:
            return f"past-{_iso_week(monday)}", "past", monday
        return "ongoing", "ongoing", None
    if monday > week0 + timedelta(weeks=1) and _has_deadline(e, now):
        return "deadlines", "deadlines", None
    if monday > week0 + timedelta(weeks=SHARD_WEEKS):
        return "later", "later", None
    return _iso_week(monday), "week", monday


def _shard_file(city_dir: Path, folder: str, key: str, data: str, written: set[Path]) -> ShardFile:
    raw = data.encode()
    digest = hashlib.sha256(raw).hexdigest()
    rel = f"{folder}/{key}.{digest[:HASH_CHARS]}.json" if folder else f"{key}.{digest[:HASH_CHARS]}.json"
    path = city_dir / rel
    if not path.exists():  # content-addressed: an existing file already has exactly these bytes
        _write(path, data)
    written.add(path)
    return ShardFile(file=rel, sha256=digest, bytes=len(raw))


def write_shards(cards: CityFeed, details: CityDetails, out_dir: Path, now: datetime) -> CityManifest:
    """Split the card feed into week shards + matching details shards, write them and the manifest (atomic, last).

    Files no longer listed in the manifest are removed, so the published site never grows without bound."""
    tz = ZoneInfo(cards.timezone)
    week0 = _monday(now.astimezone(tz).date())
    groups: dict[str, tuple[ShardKind, date | None, list[Event]]] = {}
    for e in cards.events:  # feed order is kept inside every shard; the client merges by (start, id)
        key, kind, monday = shard_of(e, tz, week0, now)
        groups.setdefault(key, (kind, monday, []))[2].append(e)
    city_dir = out_dir / "cities" / cards.city
    written: set[Path] = set()
    refs: list[ShardRef] = []
    order: dict[str, int] = {"ongoing": 0, "deadlines": 1, "week": 2, "openings": 3, "later": 4, "past": 5}
    parts: list[tuple[str, ShardKind, date | None, list[Event]]] = []
    for key, (kind, monday, events) in sorted(groups.items(), key=lambda kv: (order[kv[1][0]], kv[0])):
        for i in range(0, len(events), SHARD_EVENTS):
            parts.append(
                (key if i == 0 else f"{key}.{i // SHARD_EVENTS + 1}", kind, monday, events[i : i + SHARD_EVENTS])
            )
    for key, kind, monday, events in parts:
        shard = CityShard(city=cards.city, key=key, events=events)
        det = CityShardDetails(
            city=cards.city, key=key, events={e.id: details.events[e.id] for e in events if e.id in details.events}
        )
        refs.append(
            ShardRef(
                key=key,
                kind=kind,
                starts=monday,
                ends=monday + timedelta(weeks=1) if monday else None,
                events=len(events),
                cards=_shard_file(city_dir, "w", key, shard.model_dump_json(exclude_none=True), written),
                details=_shard_file(city_dir, "d", key, det.model_dump_json(exclude_none=True), written),
            )
        )
    meta = cards.model_copy(update={"events": []})
    manifest = CityManifest(
        generated_at=cards.generated_at,
        city=cards.city,
        timezone=cards.timezone,
        current_week=_iso_week(week0),
        meta=_shard_file(city_dir, "", "meta", meta.model_dump_json(exclude_none=True), written),
        shards=refs,
        legacy=f"../{cards.city}.json",
    )
    _write(city_dir / "manifest.json", manifest.model_dump_json(exclude_none=True))
    for p in [*city_dir.glob("meta.*.json"), *city_dir.glob("w/*.json"), *city_dir.glob("d/*.json")]:
        if p not in written:
            p.unlink()
    return manifest


def export_all(
    db: Database,
    reg: Registry,
    out_dir: Path,
    now: datetime,
    include_demo: bool = False,
    failed_builds: set[str] | None = None,
) -> dict[str, Any]:
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
    rel = reliability(db, now)
    for city in reg.cities.values():
        if not city.enabled:
            continue
        if failed_builds and city.slug in failed_builds and not (out_dir / "cities" / f"{city.slug}.json").exists():
            # no last-known-good file (fresh CI checkout) and this run's build failed: leave the city out rather
            # than publish it with zero events. It comes back on the next good build; HEALTH.md shows the error.
            log.warning("not exporting %s: build failed and there is no previous export", city.slug)
            continue
        feed = city_feed(db, reg, city, now, include_demo)
        scores = {
            s.source_id: (r.score if (r := rel.get(f"{s.source_id}@{city.slug}")) else None) for s in feed.sources
        }
        ranked = annotate(feed.events, scores, now)  # before summaries are cut
        # one deterministic order (start instant, then id) that the web client reproduces when it merges shards
        feed = feed.model_copy(update={"events": sorted(ranked, key=lambda e: (e.start, e.id))})
        feed.coverage = gate_city(db, reg, city, now, feed.events)  # ADR-0008: go-live tier + coverage block
        CityFeed.model_validate(feed.model_dump())  # belt and braces: never export an invalid document
        cards, details = split_feed(feed)
        cards_json, details_json = cards.model_dump_json(exclude_none=True), details.model_dump_json(exclude_none=True)
        paths = [
            out_dir / "cities" / f"{city.slug}.json",
            out_dir / "cities" / f"{city.slug}.details.json",
            out_dir / "cities" / city.slug / "manifest.json",
        ]
        fh = f"{feed_hash(cards_json, details_json)}:shards-v{SHARD_VERSION}"
        if not export_unchanged(db, city.slug, fh, paths):  # incremental: identical feeds aren't rewritten
            _write(paths[0], cards_json)
            _write(paths[1], details_json)
            write_shards(cards, details, out_dir, now)
            mark_exported(db, city.slug, fh, now)
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
                    if e.registration
                    and e.registration.closes_at
                    and e.registration.closes_at >= now
                    and e.registration.method != Method.DERIVED
                ),
                "sources_ok": sum(1 for s in feed.sources if s.state in ("healthy", "recovering")),
                "sources_total": sum(1 for s in feed.sources if s.state != "disabled"),
                "sources_disabled": sum(1 for s in feed.sources if s.state == "disabled"),
                "stale_sources": sum(1 for s in feed.sources if s.stale and s.state != "disabled"),
                "tier": feed.coverage.tier,
                "coverage": json.loads(feed.coverage.model_dump_json(exclude_none=True)),
            }
        )
        for s in feed.sources:
            r = rel.get(f"{s.source_id}@{city.slug}")
            health["units"].append(
                {
                    "city": city.slug,
                    **json.loads(s.model_dump_json()),
                    "reliability": None if r is None else {"grade": r.grade, "score": r.score, "attempts": r.attempts},
                }
            )
    _write(out_dir / "index.json", json.dumps(index, separators=(",", ":")))
    log_rows = db.all("SELECT at, unit, level, kind, message FROM health_log ORDER BY id DESC LIMIT 200")
    health["log"] = [dict(r) for r in log_rows]
    _write(out_dir / "health.json", json.dumps(health, separators=(",", ":")))
    return index
