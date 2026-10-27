"""I-117: week-sharded city data. Every card lands in exactly one shard; files are content-addressed; the
manifest lists them; stale files are removed."""

import json
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from gotc.pipeline.export import shard_of, split_feed, write_shards
from gotc.schema import CityFeed, CityManifest, CityShard, CityShardDetails, Event

NOW = datetime(2026, 10, 21, 15, 0, tzinfo=UTC)  # a Wednesday
TZ = ZoneInfo("America/Chicago")
WEEK0 = datetime(2026, 10, 19).date()


def ev(i: str, start: datetime, **kw: object) -> Event:
    d: dict[str, object] = {
        "id": f"evt_{i}",
        "city": "testville",
        "title": f"Event {i}",
        "summary": f"About event {i}.",
        "kind": "one_off",
        "category": "music.concert",
        "start": start,
        "timezone": "America/Chicago",
        "location": {"venue_name": "Hall"},
        "price": {},
        "sources": [{"source_id": "s", "record_id": i, "fetched_at": NOW}],
        "provenance": {"title": {"source": "s", "fetched_at": NOW}},
        "first_seen": NOW,
        "last_checked": NOW,
    }
    d.update(kw)
    return Event.model_validate(d)


def feed(events: list[Event]) -> CityFeed:
    return CityFeed(
        generated_at=NOW,
        city="testville",
        city_name="Testville",
        state="MN",
        timezone="America/Chicago",
        center=(45.0, -93.0),
        events=events,
    )


def test_shard_assignment():
    key = lambda e: shard_of(e, TZ, WEEK0, NOW)[0]  # noqa: E731
    assert key(ev("a", NOW)) == "2026-W43"
    # Sunday 11 pm in Chicago is still the same ISO week, even though it's Monday in UTC
    assert key(ev("b", datetime(2026, 10, 26, 4, 30, tzinfo=UTC))) == "2026-W43"
    assert key(ev("c", NOW + timedelta(days=7))) == "2026-W44"
    assert key(ev("d", NOW - timedelta(days=10), end=NOW + timedelta(days=20))) == "ongoing"
    assert (
        key(ev("e", NOW - timedelta(days=60), kind="opening", category="food_drink.restaurant_opening")) == "openings"
    )
    assert key(ev("e2", NOW - timedelta(days=4))) == "past-2026-W42"  # last week, over
    assert key(ev("e3", NOW - timedelta(days=1))) == "2026-W43"  # earlier this week stays in its week
    league = ev("f", NOW + timedelta(days=60), registration={"closes_at": NOW + timedelta(days=5)})
    assert key(league) == "deadlines"
    past_deadline = ev("g", NOW + timedelta(days=60), registration={"closes_at": NOW - timedelta(days=5)})
    assert key(past_deadline) == "2026-W51"
    assert key(ev("h", NOW + timedelta(days=200))) == "later"


def test_write_shards_roundtrip_and_cleanup(tmp_path):
    events = [
        ev("a", NOW),
        ev("b", NOW + timedelta(days=8)),
        ev("c", NOW - timedelta(days=9), end=NOW + timedelta(days=9)),
        ev("d", NOW + timedelta(days=300)),
    ]
    cards, details = split_feed(feed(events))
    m = write_shards(cards, details, tmp_path, NOW)
    city = tmp_path / "cities" / "testville"
    on_disk = CityManifest.model_validate_json((city / "manifest.json").read_text())
    assert on_disk == m and m.current_week == "2026-W43" and m.legacy == "../testville.json"
    assert [s.key for s in m.shards] == ["ongoing", "2026-W43", "2026-W44", "later"]
    seen: list[str] = []
    for s in m.shards:
        shard = CityShard.model_validate_json((city / s.cards.file).read_text())
        det = CityShardDetails.model_validate_json((city / s.details.file).read_text())
        assert s.cards.sha256[:10] in s.cards.file and (city / s.cards.file).stat().st_size == s.cards.bytes
        assert len(shard.events) == s.events and set(det.events) == {e.id for e in shard.events}
        assert all(not e.provenance for e in shard.events), "provenance stays in the details shards"
        seen += [e.id for e in shard.events]
    assert sorted(seen) == sorted(e.id for e in events), "every card is in exactly one shard"
    week = next(s for s in m.shards if s.key == "2026-W43")
    assert str(week.starts) == "2026-10-19" and str(week.ends) == "2026-10-26"
    meta = CityFeed.model_validate_json((city / m.meta.file).read_text())
    assert meta.events == [] and meta.city_name == "Testville"

    # a changed event gets a new file name; the old file is removed, unchanged shards keep theirs
    old = {s.key: s.cards.file for s in m.shards}
    events[0] = ev("a", NOW, title="Event a, moved")
    cards, details = split_feed(feed(events))
    m2 = write_shards(cards, details, tmp_path, NOW)
    new = {s.key: s.cards.file for s in m2.shards}
    assert new["2026-W43"] != old["2026-W43"] and not (city / old["2026-W43"]).exists()
    assert new["later"] == old["later"]
    listed = {s.cards.file for s in m2.shards} | {s.details.file for s in m2.shards} | {m2.meta.file}
    files = {str(p.relative_to(city)) for p in city.rglob("*.json")} - {"manifest.json"}
    assert files == listed
    assert json.loads((city / "manifest.json").read_text())["schema_version"] == m2.schema_version


def test_busy_weeks_split_into_parts(tmp_path, monkeypatch):
    import gotc.pipeline.export as ex

    monkeypatch.setattr(ex, "SHARD_EVENTS", 2)
    events = [ev(str(i), NOW + timedelta(minutes=i)) for i in range(5)]
    cards, details = split_feed(feed(events))
    m = write_shards(cards, details, tmp_path, NOW)
    assert [(s.key, s.events) for s in m.shards] == [("2026-W43", 2), ("2026-W43.2", 2), ("2026-W43.3", 1)]
    assert {str(s.starts) for s in m.shards} == {"2026-10-19"}
