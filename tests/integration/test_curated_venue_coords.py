"""G8: an event that only names a curated venue (or one of its aliases) takes the venue's sourced coordinates, even
when an earlier build already stored that alias as its own coordinate-less venue."""

from datetime import timedelta

from gotc.pipeline import build as buildmod
from gotc.pipeline.build import build_city
from gotc.pipeline.resolve import VenueEntity
from gotc.pipeline.textnorm import norm_venue
from gotc.schema import Event, SourceEvent
from gotc.storage.db import iso
from tests.conftest import NOW, make_city, make_registry, make_source

SRC = make_source("lib_ics", "ics", url="https://cal.example/lib.ics")
CITY = make_city("testville", [SRC])
REG = make_registry(CITY)


def _record(db, rid: str, venue: str) -> None:
    ev = SourceEvent(
        source_id=SRC.id,
        record_id=rid,
        city=CITY.slug,
        title=f"Storytime {rid}",
        category="family.kids",
        start=NOW + timedelta(days=1),
        timezone=CITY.timezone,
        fetched_at=NOW,
        location={"venue_name": venue, "address": f"Gellman Room - {venue}"},
    )
    db.execute(
        "INSERT INTO source_records (source_id, record_id, city, unit, data, content_hash, start_at, first_seen,"
        " last_seen) VALUES (?,?,?,?,?,?,?,?,?)",
        (SRC.id, rid, CITY.slug, f"{SRC.id}@{CITY.slug}", ev.model_dump_json(), rid, iso(ev.start), iso(NOW), iso(NOW)),
    )


def test_curated_alias_places_events_and_beats_a_stored_coordinateless_venue(db, monkeypatch):
    base = VenueEntity(
        "ven_curated",
        "Richmond Public Library – Main Library",
        norm_venue("Richmond Public Library – Main Library"),
        37.5433,
        -77.4427,
        "101 East Franklin Street, Richmond, VA 23219",
    )
    alias = VenueEntity(**{**base.__dict__, "norm": norm_venue("Main Library")})
    monkeypatch.setattr(buildmod, "load_curated_venues", lambda slug: [base, alias])
    # an earlier build (before the alias was curated) stored "Main Library" as its own venue, without coordinates
    db.execute(
        "INSERT INTO venues (id, city, name, norm_name, updated_at) VALUES (?,?,?,?,?)",
        ("ven_learned", CITY.slug, "Main Library", norm_venue("Main Library"), iso(NOW)),
    )
    _record(db, "a", "Main Library")
    _record(db, "b", "Richmond Public Library – Main Library")
    build_city(db, REG, CITY, NOW)
    evs = [Event.model_validate_json(r["data"]) for r in db.all("SELECT data FROM events WHERE city = ?", (CITY.slug,))]
    assert len(evs) == 2
    for e in evs:
        assert (e.location.lat, e.location.lon) == (37.5433, -77.4427)
        assert e.venue_id == "ven_curated"
        assert e.location.address == "Gellman Room - " + (e.location.venue_name or "")  # the room stays visible
