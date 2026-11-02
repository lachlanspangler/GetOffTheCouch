"""The gate runs inside build: non-events are quarantined with a reason, counted in HEALTH.md, and never exported."""

from __future__ import annotations

from datetime import timedelta

from gotc.health.report import render
from gotc.pipeline.build import build_city
from gotc.pipeline.ingest import store_ingest_skips
from gotc.schema import SourceEvent
from gotc.storage.db import iso
from tests.conftest import NOW, make_city, make_registry, make_source, unit_for

SRC = make_source("uni_events", adapter="localist", audience_filter="institution")
CITY = make_city("testville", [SRC])
REG = make_registry(CITY)


def put(db, title: str, category: str = "other.uncategorized", **kw) -> None:
    ev = SourceEvent.model_validate(
        {
            "source_id": SRC.id,
            "record_id": title,
            "city": CITY.slug,
            "title": title,
            "category": category,
            "start": NOW + timedelta(days=3),
            "timezone": CITY.timezone,
            "fetched_at": NOW,
            **kw,
        }
    )
    db.execute(
        "INSERT INTO source_records (source_id, record_id, city, unit, data, content_hash, start_at, first_seen,"
        " last_seen) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            SRC.id,
            title,
            CITY.slug,
            f"{SRC.id}@{CITY.slug}",
            ev.model_dump_json(),
            title,
            iso(ev.start),
            iso(NOW),
            iso(NOW),
        ),
    )


def test_build_quarantines_non_events_and_health_counts_them(db):
    put(db, "Fall B: Last day to withdraw from the University with a 25% refund of tuition", "learning.networking")
    put(db, "Holiday Closure - Election Day")
    put(db, "Fall Choral Concert", "music.classical", category_basis="source_label")
    stats = build_city(db, REG, CITY, NOW, geocoder=None)
    assert stats.records == 3 and stats.gated == 2 and stats.events == 1
    titles = [r["title"] for r in db.all("SELECT data ->> '$.title' title FROM events")]
    assert titles == ["Fall Choral Concert"]
    held = {r["rule"]: r for r in db.all("SELECT * FROM gated_listings WHERE stage = 'build'")}
    assert set(held) == {"academic_calendar", "closure"}
    assert all(r["reason"] and r["evidence"] for r in held.values())
    # a rebuild replaces the build-stage snapshot instead of piling up rows
    build_city(db, REG, CITY, NOW, geocoder=None)
    assert db.one("SELECT COUNT(*) c FROM gated_listings")["c"] == 2

    store_ingest_skips(
        db, unit_for(SRC, CITY), [("x1", "Webinar (Virtual)", None, "ingest:location", "online-only")], NOW
    )
    md = render(db, REG, NOW)
    assert "## Held back: not real public events" in md
    row = next(
        line
        for line in md.splitlines()
        if line.startswith("| `uni_events@testville`") and "Held" not in line and "closure" in line
    )
    assert "| 3 | 2 | 1 |" in row and "academic_calendar 1" in row


def test_withdrawal_deadline_never_reaches_the_export(db, settings):
    from gotc.pipeline.export import city_feed

    put(db, "Fall B: Last day to withdraw from the University with a 25% refund of tuition", "learning.networking")
    put(db, "Fall Choral Concert", "music.classical", category_basis="source_label")
    build_city(db, REG, CITY, NOW, geocoder=None)
    feed = city_feed(db, REG, CITY, NOW)
    assert [e.title for e in feed.events] == ["Fall Choral Concert"]
    [status] = feed.sources
    assert status.held_back == 1
