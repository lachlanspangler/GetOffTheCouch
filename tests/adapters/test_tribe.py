"""The Events Calendar (WordPress) adapter against a real recorded MPRB payload (tests/fixtures/mprb_events)."""

from gotc.adapters.base import ParseContext, Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.conftest import NOW, fixture_bytes, make_city, make_source, unit_for

SRC = make_source(
    "mprb_events", "tribe", base_url="https://www.minneapolisparks.org", default_category="outdoors.park",
    category_map={"Environmental Volunteer Opportunities": "volunteer.one_off"},
)
UNIT = unit_for(SRC, make_city("minneapolis", [SRC]))


def payload():
    return Payload("https://www.minneapolisparks.org/wp-json/tribe/events/v1/events", 200,
                   fixture_bytes("mprb_events/payload_0.json"), NOW)


def test_parses_every_record_without_rejects():
    parsed = parse_payloads(get_adapter("tribe"), UNIT, [(payload(), None)], NOW)
    assert len(parsed.valid) == 12 and not parsed.rejects


def test_fields_map_correctly():
    parsed = parse_payloads(get_adapter("tribe"), UNIT, [(payload(), None)], NOW)
    by_id = {ev.record_id: ev for ev, _ in parsed.valid}
    rose = by_id["10013781"]
    assert rose.title == "Rose Garden Volunteering"
    assert rose.category == "volunteer.one_off"  # via category_map
    assert rose.start.isoformat() == "2026-10-17T09:00:00-05:00"  # local time in the venue's zone
    assert rose.location.venue_name == "Lyndale Park/Rose Garden"
    assert rose.location.lat is not None
    # I-012: the SignUpGenius link inside the description HTML became a registration offer
    assert any(o.seller == "SignUpGenius" and o.kind == "registration" for o in rose.offers)
    # I-015: volunteering is free, by definition
    assert rose.price.is_free
    # entities are unescaped
    assert by_id["10013435"].title == "Early Birders – October"


def test_location_recovered_from_description_when_venue_missing():
    parsed = parse_payloads(get_adapter("tribe"), UNIT, [(payload(), None)], NOW)
    ev = next(e for e, _ in parsed.valid if e.record_id == "10014418")
    assert ev.location.venue_name == "Minnehaha Regional Park"
    assert ev.extras.get("location_from") == "description"


def test_parse_is_pure():
    a = list(get_adapter("tribe").parse(payload(), ParseContext(UNIT, NOW)))
    b = list(get_adapter("tribe").parse(payload(), ParseContext(UNIT, NOW)))
    assert a == b
