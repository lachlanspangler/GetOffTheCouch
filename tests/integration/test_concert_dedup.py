"""The same show from a venue's own calendar (real recorded JSON-LD) and a Ticketmaster-shaped record merges
into ONE event that keeps both sellers' prices and buy links."""

from datetime import timedelta

from gotc.pipeline.resolve import cluster_events, resolve_venues
from gotc.schema import SourceEvent
from tests.adapters.test_jsonld import _real
from tests.conftest import make_city


def test_venue_calendar_and_ticketmaster_merge():
    venue_events = [e for e, _ in _real("icehouse_mpls").valid]
    assert venue_events, "fixture should parse"
    show = venue_events[0]
    tm = SourceEvent(
        source_id="ticketmaster",
        record_id="vvX",
        city=show.city,
        title=show.title.upper() + " | Tickets",
        category="music.concert",
        start=show.start + timedelta(minutes=30),
        timezone=show.timezone,
        fetched_at=show.fetched_at,
        location={"venue_name": "Icehouse - Minneapolis"},
        price={"min": 15, "max": 20},
        url="https://www.ticketmaster.com/event/vvX",
        offers=[
            {
                "seller": "Ticketmaster",
                "kind": "primary",
                "url": "https://www.ticketmaster.com/event/vvX",
                "price_min": 15,
                "price_max": 20,
                "source_id": "ticketmaster",
                "fetched_at": show.fetched_at,
            }
        ],
    )
    other = venue_events[1] if len(venue_events) > 1 else None
    records = [show, tm] + ([other] if other else [])
    city = make_city("minneapolis")
    clusters = cluster_events(records, resolve_venues(records, city, []), city.timezone)
    merged = next(c for c in clusters if any(m.source_id == "ticketmaster" for m in c.members))
    assert {m.source_id for m in merged.members} == {"ticketmaster", "icehouse_mpls"}
    if other:
        assert all(other not in c.members or len(c.members) == 1 for c in clusters)
