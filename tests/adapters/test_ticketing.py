"""Ticketmaster + SeatGeek parsers against SYNTHETIC fixtures in the documented shapes (no keys yet).

When keys exist: `gotc record ticketmaster@minneapolis --trim 8` and add real-fixture tests alongside these.
"""

from datetime import UTC, datetime

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from gotc.pipeline.resolve import cluster_events, resolve_venues
from gotc.schema import DataType
from tests.conftest import fixture_bytes, make_city, make_source, unit_for

NOW = datetime(2026, 10, 16, 15, tzinfo=UTC)
CITY = make_city("minneapolis")


def parse(adapter: str, fixture: str):
    src = make_source(adapter, adapter, data_type=DataType.TICKET_PRICES)
    p = Payload("https://api.example/", 200, fixture_bytes(f"synthetic/{fixture}"), NOW)
    return parse_payloads(get_adapter(adapter), unit_for(src, CITY), [(p, None)], NOW)


def test_ticketmaster_fields_status_and_rejects():
    parsed = parse("ticketmaster", "ticketmaster_events.json")
    evs = {e.record_id: e for e, _ in parsed.valid}
    assert set(evs) == {"vvTEST1", "vvTEST2", "vvTEST3"}
    assert len(parsed.rejects) == 1  # the record with no name/start
    band = evs["vvTEST1"]
    assert band.category == "music.concert"
    assert band.start.isoformat() == "2026-11-07T20:00:00-06:00"  # UTC dateTime shown in venue tz
    assert band.price.min == 39.5 and band.price.max == 89.5 and "face value" in (band.price.note or "")
    o = band.offers[0]
    assert o.kind == "primary" and o.seller == "Ticketmaster" and o.fees_included is False
    assert band.location.lat == 44.975 and band.location.venue_name == "Example Theater"
    assert evs["vvTEST2"].category == "nightlife.comedy"
    assert evs["vvTEST2"].availability == "not_yet_on_sale"  # public onsale is after the fetch
    assert evs["vvTEST2"].price.min is None  # priceRanges absent → we don't guess
    reg = evs["vvTEST2"].registration
    assert reg and reg.opens_at and reg.method == "reported" and "Public on-sale" in (reg.evidence or "")
    assert evs["vvTEST1"].registration is None  # already on sale → no on-sale deadline
    assert evs["vvTEST3"].availability == "cancelled"


def test_seatgeek_resale_stats_capacity_and_sports():
    parsed = parse("seatgeek", "seatgeek_events.json")
    evs = {e.record_id: e for e, _ in parsed.valid}
    band = evs["9001"]
    o = band.offers[0]
    assert o.kind == "resale" and o.listing_count == 112 and o.price_min == 58
    assert band.venue_capacity == 1800
    assert evs["9002"].category == "sports_watch.game"
    assert evs["9002"].availability == "sold_out" and evs["9002"].venue_capacity is None


def test_same_show_on_both_sellers_merges_into_one_event():
    tm = [e for e, _ in parse("ticketmaster", "ticketmaster_events.json").valid]
    sg = [e for e, _ in parse("seatgeek", "seatgeek_events.json").valid]
    records = tm + sg
    vof = resolve_venues(records, CITY, [])
    clusters = cluster_events(records, vof, CITY.timezone)
    band = next(c for c in clusters if any(m.title == "The Placeholder Band" for m in c.members))
    assert {m.source_id for m in band.members} == {"ticketmaster", "seatgeek"}
    assert band.members[0].source_id == "ticketmaster"  # face-value source leads
