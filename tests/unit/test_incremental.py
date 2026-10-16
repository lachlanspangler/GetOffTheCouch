"""Incremental builds/exports (SCALING.md §4.6 item 4): unchanged cities are neither rebuilt nor rewritten."""

from datetime import timedelta

from gotc.pipeline.incremental import MAX_AGE, feed_hash, inputs_hash, mark_built, needs_build
from gotc.pipeline.run import run
from tests.conftest import NOW, fast_client, make_city, make_registry
from tests.integration.test_pipeline import REG, healthy_transport


def test_needs_build_rules(db):
    city = make_city()
    reg = make_registry(city)
    h = inputs_hash(db, reg, city)
    assert needs_build(db, city.slug, h, NOW) == (True, "never built")
    mark_built(db, city.slug, h, NOW)
    assert needs_build(db, city.slug, h, NOW + timedelta(minutes=50))[0] is False
    assert needs_build(db, city.slug, h, NOW + MAX_AGE)[0] is True  # time-dependent fields need a refresh
    db.execute(
        "INSERT INTO source_records (source_id, record_id, city, unit, data, content_hash, start_at, first_seen,"
        " last_seen) VALUES ('s', 'r1', 'testville', 's@testville', '{}', 'abc', ?, ?, ?)",
        (NOW.isoformat(), NOW.isoformat(), NOW.isoformat()),
    )
    assert inputs_hash(db, reg, city) != h  # a new record changes the inputs
    changed = make_city().model_copy(update={"radius_km": 30})
    assert inputs_hash(db, make_registry(changed), changed) != inputs_hash(db, reg, city)  # so does config


def test_slim_ci_state_always_rebuilds(db):
    city = make_city()
    reg = make_registry(city)
    h = inputs_hash(db, reg, city)
    mark_built(db, city.slug, h, NOW)
    db.execute(
        "INSERT INTO events (id, city, data, start_at, category, first_seen, updated_at)"
        " VALUES ('e1', 'testville', '{}', ?, 'other', ?, ?)",
        (NOW.isoformat(), NOW.isoformat(), NOW.isoformat()),
    )
    assert needs_build(db, city.slug, h, NOW) == (True, "slim CI state (events re-derived)")


def test_second_run_skips_unchanged_city_and_keeps_files(db, settings):
    t = healthy_transport()
    first = run(db, REG, settings, client=fast_client(t), now=NOW, geocode=False)
    assert [b.city for b in first.builds] == ["minneapolis"] and not first.skipped_builds
    path = settings.web_data_dir / "cities" / "minneapolis.json"
    before = path.stat().st_mtime_ns
    second = run(db, REG, settings, client=fast_client(t), now=NOW + timedelta(minutes=30), geocode=False)
    assert second.skipped_builds == ["minneapolis"] and not second.builds
    assert "unchanged, not rebuilt" in second.summary()
    assert path.stat().st_mtime_ns == before  # identical feed → file not rewritten
    path.unlink()
    run(db, REG, settings, client=fast_client(t), now=NOW + timedelta(minutes=40), geocode=False)
    assert path.exists()  # a missing file is always rewritten
    forced = run(db, REG, settings, client=fast_client(t), now=NOW + timedelta(minutes=45), geocode=False,
                 force_build=True)  # fmt: skip
    assert [b.city for b in forced.builds] == ["minneapolis"]


def test_feed_hash_ignores_generated_at():
    a = '{"generated_at": "2026-10-16T01:00:00Z", "events": [1], "coverage": {"evaluated_at": "x", "tier": "live"}}'
    b = '{"generated_at": "2026-10-16T02:00:00Z", "events": [1], "coverage": {"evaluated_at": "y", "tier": "live"}}'
    c = '{"generated_at": "2026-10-16T02:00:00Z", "events": [2]}'
    assert feed_hash(a, "{}") == feed_hash(b, "{}") != feed_hash(c, "{}")
