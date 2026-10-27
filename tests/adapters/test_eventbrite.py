"""Eventbrite v3 organizer events against a SYNTHETIC fixture in the documented shape (no token yet).
When a token exists: `gotc record eventbrite@<city> --trim 5` and add a real-fixture test."""

from datetime import UTC, datetime

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.conftest import fixture_bytes, make_city, make_source, unit_for

NOW = datetime(2026, 10, 16, 15, tzinfo=UTC)


def test_eventbrite_maps_prices_free_rsvp_and_skips_online() -> None:
    src = make_source("eventbrite", "eventbrite")
    p = Payload(
        "https://www.eventbriteapi.com/v3/organizers/1/events/",
        200,
        fixture_bytes("synthetic/eventbrite_events.json"),
        NOW,
    )
    parsed = parse_payloads(get_adapter("eventbrite"), unit_for(src, make_city("minneapolis")), [(p, None)], NOW)
    evs = {e.record_id: e for e, _ in parsed.valid}
    assert set(evs) == {"1000000000001", "1000000000002"}
    assert any("online" in err for _, err, _ in parsed.rejects)
    paid, free = evs["1000000000001"], evs["1000000000002"]
    assert paid.price.min == 15 and paid.price.max == 25 and paid.offers[0].kind == "primary"
    assert paid.location.lat == 44.98 and paid.organizer == "Example Social Club"
    assert free.price.is_free and free.offers[0].kind == "rsvp" and free.offers[0].price_min is None
