"""RSS + event-module adapter: real recorded carbonhouse feeds (ACL Live, Denver Arts & Venues) + edge cases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from gotc.adapters.base import ParseContext, Payload, get_adapter
from gotc.http.client import RobotsDisallowed
from gotc.pipeline.ingest import Parsed, parse_payloads
from gotc.schema import DataType
from gotc.settings import Settings
from tests.adapters._util import by_id, client, fetch_ctx, parse, unit
from tests.conftest import NOW, FixtureTransport, make_city, make_source, unit_for

ACL = unit("acl_live")
DAV = unit("denver_arts_venues")
FEED = "https://venue.test/events/rss"


def _rss(*items: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="utf-8"?><rss version="2.0" xmlns:ev="http://purl.org/rss/1.0/modules/event/">'
        "<channel><title>Venue</title>" + "".join(items) + "</channel></rss>"
    ).encode()


def _item(title: str = "Band", start: str = "2026-10-20T01:00:00Z", end: str | None = None, **extra: str) -> str:
    tags = "".join(f"<ev:{k}>{v}</ev:{k}>" for k, v in extra.items())
    end_tag = f"<ev:enddate>{end}</ev:enddate>" if end else ""
    return (
        f"<item><title>{title}</title><link>https://venue.test/events/{title.lower()}</link>"
        f"<description>&lt;p&gt;{title} live&lt;/p&gt;</description>"
        f"<ev:startdate>{start}</ev:startdate>{end_tag}{tags}</item>"
    )


def _unit(**params: Any):
    params.setdefault("default_category", "music.concert")
    src = make_source("venue_rss", "rss_events", DataType.CONCERTS, url=FEED, **params)
    return unit_for(src, make_city("minneapolis", [src]))


def _parse(content: bytes, **params: Any) -> Parsed:
    return parse_payloads(
        get_adapter("rss_events"), _unit(**params), [(Payload(FEED, 200, content, NOW, "xml"), None)], NOW
    )


# ───────────────────────────── real recorded feeds ─────────────────────────────


def test_real_feeds_parse_without_rejects():
    for u, n in ((ACL, 8), (DAV, 12)):
        parsed = parse(u, f"{u.source.id}/payload_0.xml")
        assert len(parsed.valid) == n and not parsed.rejects, u.source.id


def test_acl_live_utc_start_becomes_city_wall_clock():
    evs = {ev.title: ev for ev in by_id(parse(ACL, "acl_live/payload_0.xml")).values()}
    paradox = evs["The Paradox"]
    # ev:startdate 2026-10-17T01:00:00Z = 8 PM CDT, as the event URL says ("…-the-paradox-at-8-pm")
    assert paradox.start.isoformat() == "2026-10-16T20:00:00-05:00"
    assert paradox.end is None  # the feed repeats the start as the end
    assert paradox.location.venue_name == "ACL Live at 3TEN"
    assert paradox.location.address == "310 W Willie Nelson Blvd, Austin, TX 78701"
    assert str(paradox.url) == "https://www.acllive.com/events/detail/2026-10-16-the-paradox-at-8-pm"
    assert paradox.category == "music.concert" and paradox.price.min is None


def test_denver_arts_venues_rooms_map_to_categories_and_addresses():
    evs = {ev.title: ev for ev in by_id(parse(DAV, "denver_arts_venues/payload_0.xml")).values()}
    tempest = evs["The Tempest"]
    assert tempest.category == "arts.theater" and tempest.location.venue_name == "Kilstrom Theatre"
    assert tempest.start.isoformat() == "2026-10-16T19:00:00-06:00"
    assert tempest.end is not None and tempest.end.isoformat() == "2026-11-01T13:30:00-07:00"  # a run (after DST ends)
    assert evs["Joe Hisaishi with the Colorado Symphony"].category == "music.classical"
    assert evs["Kelly Green Trio"].location.address == "1512 Curtis St, Denver, CO 80202"  # `venues` override
    assert evs["Kelly Green Trio"].category == "music.concert"
    rocky = evs["Denver Film Festival49 | Opening Night Presentation: I Play Rocky"]
    assert rocky.category == "arts.theater"  # "Opening Night" title keyword, not a bar opening
    assert rocky.location.address == "1400 Curtis St, Denver, CO 80202"  # default venue address
    assert evs["Kids' Matinee: The Playmakers, The Wizard of Oz, an interactive event"].start.hour == 12


# ───────────────────────────── edge cases ─────────────────────────────


def test_windowing_end_equal_start_and_missing_fields():
    past = _item("Past", "2026-10-01T01:00:00Z")
    run = _item("Long Run", "2026-10-01T01:00:00Z", "2026-11-01T01:00:00Z")  # started, still running
    far = _item("Far", "2028-01-01T01:00:00Z")
    same = _item("Same", "2026-10-20T01:00:00Z", "2026-10-20T01:00:00Z", location="Main Room")
    broken = "<item><title>No Date</title></item>"
    parsed = _parse(_rss(past, run, far, same, broken), venue={"name": "The Room", "address": "1 Main St"})
    evs = {ev.title: ev for ev, _ in parsed.valid}
    assert set(evs) == {"Long Run", "Same"}
    assert evs["Same"].end is None and evs["Same"].location.venue_name == "Main Room"
    assert evs["Same"].location.address == "1 Main St"
    assert evs["Long Run"].location.venue_name == "The Room"  # no ev:location → configured venue
    assert [err for _, err, _ in parsed.rejects] == ["item without title/ev:startdate"]


def test_category_map_by_type_and_title_keyword():
    items = _rss(_item("Comedy Night"), _item("Hamlet", type="Theater"), _item("Plain Band"))
    parsed = _parse(items, category_map={"Theater": "arts.theater", "comedy": "nightlife.comedy"})
    cats = {ev.title: ev.category for ev, _ in parsed.valid}
    assert cats == {"Comedy Night": "nightlife.comedy", "Hamlet": "arts.theater", "Plain Band": "music.concert"}


def test_parse_is_pure():
    payload = Payload(FEED, 200, _rss(_item()), NOW, "xml")
    a = list(get_adapter("rss_events").parse(payload, ParseContext(_unit(), NOW)))
    b = list(get_adapter("rss_events").parse(payload, ParseContext(_unit(), NOW)))
    assert a == b


# ───────────────────────────── fetch ─────────────────────────────


def test_fetch_returns_the_feed(transport: FixtureTransport, settings: Settings, tmp_path: Path):
    transport.add(r"/events/rss$", _rss(_item()))
    fr = get_adapter("rss_events").fetch(fetch_ctx(_unit(), client(transport, tmp_path), settings))
    assert len(fr.payloads) == 1 and fr.complete and fr.payloads[0].content_type == "xml"


@pytest.mark.parametrize(
    ("body", "match"),
    [
        (b"<html>redesigned</html>", "not well-formed|did not return an RSS"),
        (b'<rss version="2.0"><channel><item><title>News</title></item></channel></rss>', "no ev:startdate"),
        (b'<!DOCTYPE rss [<!ENTITY x "y">]><rss/>', "DOCTYPE"),
    ],
)
def test_fetch_rejects_non_event_feeds(
    body: bytes, match: str, transport: FixtureTransport, settings: Settings, tmp_path: Path
):
    transport.add(r"/events/rss$", body)
    with pytest.raises(Exception, match=match):
        get_adapter("rss_events").fetch(fetch_ctx(_unit(), client(transport, tmp_path), settings))


def test_fetch_honors_robots(transport: FixtureTransport, settings: Settings, tmp_path: Path):
    transport.add(r"/robots\.txt$", "User-agent: *\nDisallow: /events/\n")
    transport.add(r"/events/rss$", _rss(_item()))
    with pytest.raises(RobotsDisallowed):
        get_adapter("rss_events").fetch(fetch_ctx(_unit(), client(transport, tmp_path), settings))
