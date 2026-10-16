"""schema.org JSON-LD adapter: synthetic edge cases + real recorded venue pages (tests/fixtures/<source_id>/)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from gotc.adapters.base import ParseContext, Payload, get_adapter
from gotc.adapters.jsonld import find_events, ld_blocks, load_block
from gotc.http.client import RobotsDisallowed
from gotc.pipeline.ingest import Parsed, parse_payloads
from gotc.schema import DataType
from gotc.settings import Settings
from tests.adapters._util import client, fetch_ctx
from tests.adapters._util import unit as real_unit
from tests.conftest import FIXTURES, NOW, FixtureTransport, make_city, make_source, unit_for

BASE = "https://venue.test/shows/"


def _unit(**params: Any):
    params.setdefault("default_category", "music.concert")
    src = make_source("venue_test", "jsonld", DataType.CONCERTS, urls=[BASE], **params)
    return unit_for(src, make_city("minneapolis", [src]))


def _page(*blocks: Any, raw: str | None = None) -> bytes:
    scripts = "".join(f'<script type="application/ld+json">{json.dumps(b)}</script>' for b in blocks)
    if raw is not None:
        scripts += f'<script type="application/ld+json">{raw}</script>'
    return f"<html><head>{scripts}</head><body>hi</body></html>".encode()


def _parse(content: bytes, url: str = BASE, **params: Any) -> Parsed:
    u = _unit(**params)
    return parse_payloads(get_adapter("jsonld"), u, [(Payload(url, 200, content, NOW, "html"), None)], NOW)


def _by_title(parsed: Parsed) -> dict[str, Any]:
    return {ev.title: ev for ev, _ in parsed.valid}


EV = {
    "@type": "MusicEvent",
    "name": "Low Band",
    "startDate": "2026-10-20T20:00:00-05:00",
    "url": "/shows/low-band/",
    "location": {
        "@type": "Place",
        "name": "The Room",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "1 Main St",
            "addressLocality": "Minneapolis",
            "addressRegion": "MN",
            "postalCode": "55401",
        },
        "geo": {"@type": "GeoCoordinates", "latitude": "44.98", "longitude": "-93.27"},
    },
}


# ───────────────────────────── structure ─────────────────────────────


def test_graph_itemlist_and_subevents_are_all_found():
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Organization", "name": "The Room"},
            {**EV, "name": "Graph Show"},
        ],
    }
    item_list = {
        "@type": "ItemList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "item": {**EV, "name": "List Show A", "url": "/a"}},
            {"@type": "ListItem", "position": 2, "item": {**EV, "name": "List Show B", "url": "/b"}},
        ],
    }
    festival = {
        "@type": "Festival",
        "name": "Room Fest",
        "startDate": "2026-10-24",
        "endDate": "2026-10-25",
        "subEvent": [
            {**EV, "name": "Fest Night 1", "startDate": "2026-10-24T19:00:00-05:00"},
            {**EV, "name": "Fest Night 2", "startDate": "2026-10-25T19:00:00-05:00"},
        ],
    }
    array_block = [{**EV, "name": "Array Show", "url": "/arr", "@type": ["Event", "MusicEvent"]}]
    parsed = _parse(_page(graph, item_list, festival, array_block))
    titles = set(_by_title(parsed))
    assert titles == {
        "Graph Show",
        "List Show A",
        "List Show B",
        "Room Fest",
        "Fest Night 1",
        "Fest Night 2",
        "Array Show",
    }
    assert not parsed.rejects
    fest = _by_title(parsed)["Room Fest"]
    assert fest.category.endswith(".festival") and fest.all_day


def test_find_events_does_not_descend_into_publisher_or_offers():
    data = {"@type": "WebPage", "publisher": {"@type": "Event", "name": "nope"}, "about": EV}
    assert [e["name"] for e in find_events(data)] == ["Low Band"]


def test_location_address_geo_and_url_resolution():
    ev = _by_title(_parse(_page(EV)))["Low Band"]
    assert ev.location.venue_name == "The Room"
    assert ev.location.address == "1 Main St, Minneapolis, MN 55401"
    assert (ev.location.lat, ev.location.lon) == (44.98, -93.27)
    assert str(ev.url) == "https://venue.test/shows/low-band/"
    assert ev.category == "music.concert"


def test_fallback_venue_when_event_has_no_location():
    raw = {k: v for k, v in EV.items() if k != "location"}
    ev = _by_title(_parse(_page(raw), venue={"name": "Fallback Hall"}))["Low Band"]
    assert ev.location.venue_name == "Fallback Hall"


# ───────────────────────────── offers ─────────────────────────────


def test_aggregate_offer_with_tiers_maps_to_one_offer_and_price_band():
    ev = {
        **EV,
        "offers": {
            "@type": "AggregateOffer",
            "lowPrice": "25.00",
            "highPrice": "45.00",
            "priceCurrency": "USD",
            "url": "https://www.etix.com/ticket/p/1",
            "offers": [
                {
                    "@type": "Offer",
                    "price": 25,
                    "availability": "https://schema.org/SoldOut",
                    "url": "https://www.etix.com/ticket/p/1",
                },
                {
                    "@type": "Offer",
                    "price": 45,
                    "availability": "https://schema.org/InStock",
                    "url": "https://www.etix.com/ticket/p/1",
                },
            ],
        },
    }
    rec = _by_title(_parse(_page(ev)))["Low Band"]
    assert (rec.price.min, rec.price.max) == (25.0, 45.0)
    assert len(rec.offers) == 1
    offer = rec.offers[0]
    assert offer.seller == "Etix" and offer.kind.value == "primary"
    assert (offer.price_min, offer.price_max) == (25.0, 45.0)
    assert offer.availability.value == "on_sale"  # one tier still on sale
    assert rec.availability.value == "on_sale"


@pytest.mark.parametrize(
    ("availability", "expected"),
    [
        ("https://schema.org/InStock", "on_sale"),
        ("http://schema.org/SoldOut", "sold_out"),
        ("LimitedAvailability", "limited"),
        ("https://schema.org/PreOrder", "not_yet_on_sale"),
        ("inStock", "on_sale"),
    ],
)
def test_offer_availability_mapping(availability: str, expected: str):
    ev = {**EV, "offers": {"@type": "Offer", "price": "20", "priceCurrency": "USD", "availability": availability}}
    rec = _by_title(_parse(_page(ev)))["Low Band"]
    assert rec.availability.value == expected
    assert rec.offers[0].availability.value == expected
    assert str(rec.offers[0].url) == "https://venue.test/shows/low-band/"  # offer without url → event url


def test_future_valid_from_is_the_on_sale_date():
    ev = {
        **EV,
        "offers": {
            "@type": "Offer",
            "price": 30,
            "url": "https://tixr.com/e/1",
            "validFrom": "2026-10-23T10:00:00-05:00",
        },
    }
    rec = _by_title(_parse(_page(ev)))["Low Band"]
    assert rec.availability.value == "not_yet_on_sale"
    assert rec.offers[0].availability.value == "not_yet_on_sale"
    assert rec.registration is not None
    assert rec.registration.opens_at.isoformat() == "2026-10-23T10:00:00-05:00"
    assert "validFrom" in (rec.registration.evidence or "")
    assert rec.extras["onsale_at"] == "2026-10-23T10:00:00-05:00"


def test_past_valid_from_is_kept_as_extra_only_and_can_be_distrusted():
    ev = {**EV, "offers": {"@type": "Offer", "price": 30, "validFrom": "2026-07-01T00:00:00+00:00"}}
    rec = _by_title(_parse(_page(ev)))["Low Band"]
    assert rec.registration is None and rec.extras["onsale_at"] == "2026-07-01T00:00:00+00:00"
    future = {**EV, "offers": {"@type": "Offer", "price": 30, "validFrom": "2026-10-23T10:00:00-05:00"}}
    rec = _by_title(_parse(_page(future), trust_valid_from=False))["Low Band"]
    assert rec.registration is None and "onsale_at" not in rec.extras and rec.availability.value == "unknown"


def test_price_text_with_two_amounts_and_non_usd_and_zero():
    two = {**EV, "name": "Two Prices", "offers": {"@type": "Offer", "price": "$25 Advance // $30 Day of"}}
    eur = {**EV, "name": "Euro Show", "url": "/e", "offers": {"@type": "Offer", "price": 20, "priceCurrency": "EUR"}}
    zero = {**EV, "name": "Zero Show", "url": "/z", "offers": {"@type": "Offer", "price": "0"}}
    free = {**EV, "name": "Free Show", "url": "/f", "isAccessibleForFree": True}
    got = _by_title(_parse(_page(two, eur, zero, free)))
    assert (got["Two Prices"].price.min, got["Two Prices"].price.max) == (25.0, 30.0)
    assert got["Euro Show"].price.min is None and got["Euro Show"].offers[0].price_min is None
    assert not got["Zero Show"].price.is_free and got["Zero Show"].price.min is None  # 0 ≠ free by default
    assert got["Free Show"].price.is_free and got["Free Show"].availability.value == "free_no_ticket"
    assert _by_title(_parse(_page(zero), zero_is_free=True))["Zero Show"].price.is_free


# ───────────────────────────── status, time, people ─────────────────────────────


@pytest.mark.parametrize(
    ("status", "availability", "extra"),
    [
        ("https://schema.org/EventCancelled", "cancelled", "cancelled"),
        ("EventPostponed", "postponed", "postponed"),
        ("https://schema.org/EventRescheduled", "on_sale", "rescheduled"),
        ("https://schema.org/EventScheduled", "on_sale", None),
    ],
)
def test_event_status(status: str, availability: str, extra: str | None):
    ev = {**EV, "eventStatus": status, "offers": {"@type": "Offer", "price": 15, "availability": "InStock"}}
    rec = _by_title(_parse(_page(ev)))["Low Band"]
    assert rec.availability.value == availability
    assert rec.extras.get("event_status") == extra


def test_timezones_offsets_naive_and_date_only():
    aware = {**EV, "name": "Aware", "startDate": "2026-10-20T19:30:00-04:00", "url": "/a"}
    utc = {**EV, "name": "Utc", "startDate": "2026-10-21T01:00:00.000Z", "url": "/u"}
    naive = {**EV, "name": "Naive", "startDate": "2026-10-20T19:30", "endDate": "2026-10-20T23:00", "url": "/n"}
    date_only = {**EV, "name": "Dated", "startDate": "2026-10-22", "url": "/d"}
    bad_end = {**EV, "name": "Bad End", "startDate": "2026-10-22T20:00", "endDate": "2026-10-22", "url": "/x"}
    got = _by_title(_parse(_page(aware, utc, naive, date_only, bad_end)))
    assert got["Aware"].start.isoformat() == "2026-10-20T19:30:00-04:00"  # explicit offsets are respected
    assert got["Utc"].start.isoformat() == "2026-10-21T01:00:00+00:00"
    assert got["Naive"].start.isoformat() == "2026-10-20T19:30:00-05:00"  # naive → city tz (CDT)
    assert got["Naive"].end is not None and got["Naive"].end.hour == 23
    assert got["Dated"].all_day and not got["Naive"].all_day
    assert got["Bad End"].end is None  # end before start is dropped, not rejected


def test_ignore_offset_rezones_bogus_utc_stamps():
    ev = {**EV, "startDate": "2026-10-23T19:00:00+00:00"}
    rec = _by_title(_parse(_page(ev), ignore_offset=True))["Low Band"]
    assert rec.start.isoformat() == "2026-10-23T19:00:00-05:00"


def test_performers_image_and_placeholder_filtering():
    ev = {
        **EV,
        "performer": [
            {"@type": "MusicGroup", "name": "Headliner"},
            {"@type": "Person", "name": "Opener"},
            "Organization",
        ],
        "image": [{"@type": "ImageObject", "url": "/img/poster.jpg"}],
        "organizer": {"@type": "Organization", "name": "Room Presents"},
        "description": "&lt;p&gt;Doors 7pm&lt;/p&gt; &lt;a href=&quot;https://www.etix.com/ticket/p/9&quot;&gt;Tickets&lt;/a&gt;",
    }
    rec = _by_title(_parse(_page(ev)))["Low Band"]
    assert rec.extras["performers"] == "Headliner; Opener"
    assert rec.extras["image"] == "https://venue.test/img/poster.jpg"
    assert rec.organizer == "Room Presents"
    assert rec.description == "Doors 7pm\nTickets"  # entity-encoded HTML is decoded once, then flattened
    assert any(o.seller == "Etix" for o in rec.offers)  # ticket link lifted from the description HTML


def test_title_classifier_refines_music_event_and_plain_event_defaults():
    open_mic = {**EV, "name": "Tuesday Open Mic", "url": "/om"}
    comedy = {**EV, "@type": "ComedyEvent", "name": "Late Show", "url": "/c"}
    plain = {**EV, "@type": "Event", "name": "Mystery Night", "url": "/p", "description": "volunteer singles family"}
    got = _by_title(_parse(_page(open_mic, comedy, plain)))
    assert got["Tuesday Open Mic"].category == "music.open_mic"
    assert got["Late Show"].category == "nightlife.comedy"
    assert got["Mystery Night"].category == "music.concert"  # default_category; the blurb is not classified


# ───────────────────────────── rejects & windowing ─────────────────────────────


def test_rejects_and_windowing():
    no_start = {"@type": "MusicEvent", "name": "No Date"}
    past = {**EV, "name": "Last Week", "startDate": "2026-10-09T20:00:00-05:00", "url": "/old"}
    far = {**EV, "name": "Far Future", "startDate": "2028-01-01T20:00:00-06:00", "url": "/far"}
    parsed = _parse(_page(no_start, past, far, EV, raw='{"@type": "MusicEvent", "name": "broken",,}'))
    assert set(_by_title(parsed)) == {"Low Band"}
    errors = sorted(err for _, err, _ in parsed.rejects)
    assert len(errors) == 2
    assert errors[0].startswith("event without name/startDate") and "unparseable JSON-LD" in errors[1]


def test_all_day_event_today_survives_the_evening_window():
    # NOW is 22:00 local; a date-only event today must not be windowed out at midnight + 6 h
    today = {**EV, "name": "All Day Today", "startDate": "2026-10-15", "url": "/today"}
    yesterday = {**EV, "name": "All Day Yesterday", "startDate": "2026-10-14", "url": "/yday"}
    assert set(_by_title(_parse(_page(today, yesterday)))) == {"All Day Today"}


def test_date_only_keeps_the_local_date_and_drops_wrong_clock_times():
    # STG-style: two shows on one day, both stamped 7 h early; with date_only they collapse to one all-day record
    early = {**EV, "name": "Comic", "startDate": "2026-10-17T09:00:00-05:00", "url": "/comic"}
    late = {**early, "startDate": "2026-10-17T13:00:00-05:00"}
    parsed = _parse(_page(early, late), date_only=True)
    assert len(parsed.valid) == 1
    ev = parsed.valid[0][0]
    assert ev.all_day and ev.start.isoformat() == "2026-10-17T00:00:00-05:00"
    assert len(_parse(_page(early, late)).valid) == 2  # without the flag both timed records are kept


@pytest.mark.parametrize(
    ("title", "availability"),
    [
        ("An Evening with Eric Idle – CANCELED", "cancelled"),
        ("Cancelled: Story Hour", "cancelled"),
        ("Big Band (Postponed)", "postponed"),
        ("Cancel Culture Comedy Hour", "unknown"),
    ],
)
def test_cancelled_or_postponed_in_the_title(title: str, availability: str):
    ev = _by_title(_parse(_page({**EV, "name": title})))
    assert next(iter(ev.values())).availability == availability


def test_non_event_blocks_are_ignored_quietly():
    parsed = _parse(_page({"@type": "Organization", "name": "x"}, raw="{not json, no events here}"))
    assert not parsed.valid and not parsed.rejects


def test_cdata_and_html_comment_wrappers():
    raw = "<!--//--><![CDATA[//><!--\n" + json.dumps(EV) + "\n//--><!]]>"
    assert ld_blocks(_page(raw=raw).decode())  # sanity
    assert load_block("<![CDATA[" + json.dumps(EV) + "]]>")["name"] == "Low Band"
    assert load_block("<!--" + json.dumps(EV) + "-->")["name"] == "Low Band"


def test_parse_is_pure():
    u = _unit()
    pl = Payload(BASE, 200, _page(EV), NOW, "html")
    a = list(get_adapter("jsonld").parse(pl, ParseContext(u, NOW)))
    b = list(get_adapter("jsonld").parse(pl, ParseContext(u, NOW)))
    assert a == b


# ───────────────────────────── fetch ─────────────────────────────


LISTING = (
    b'<a href="/shows/a/">A</a> <a href="/shows/b/">B</a> <a href="/shows/a/">A again</a>'
    b' <a href="/shows/c/?format=ical">ics</a> <a href="/about/">about</a>'
)


def test_fetch_follows_detail_links_detail_first_and_politely(
    transport: FixtureTransport, settings: Settings, tmp_path: Path
):
    transport.add(r"/shows/a/$", _page({**EV, "name": "A"}))
    transport.add(r"/shows/b/$", _page({**EV, "name": "B", "url": "/shows/b/"}))
    transport.add(r"/shows/$", LISTING)
    u = _unit(follow=r"/shows/[^/?#]+/$")
    http = client(transport, tmp_path)
    fr = get_adapter("jsonld").fetch(fetch_ctx(u, http, settings))
    assert [p.meta["role"] for p in fr.payloads] == ["detail", "detail", "listing"]
    assert [c for c in transport.calls if not c.endswith("robots.txt")] == [
        BASE,
        "https://venue.test/shows/a/",
        "https://venue.test/shows/b/",
    ]
    assert fr.complete
    assert http.host_intervals["venue.test"] >= 2.0  # follow-ups are throttled to ≥ 2 s per host


def test_fetch_caps_follow_and_marks_incomplete(transport: FixtureTransport, settings: Settings, tmp_path: Path):
    transport.add(r"/shows/[ab]/$", _page(EV))
    transport.add(r"/shows/$", LISTING)
    fr = get_adapter("jsonld").fetch(
        fetch_ctx(_unit(follow=r"/shows/[^/?#]+/$", max_follow=1), client(transport, tmp_path), settings)
    )
    assert len(fr.payloads) == 2 and not fr.complete


def test_fetch_honors_robots(transport: FixtureTransport, settings: Settings, tmp_path: Path):
    transport.add(r"/robots\.txt$", "User-agent: *\nDisallow: /shows/\n")
    transport.add(r"/shows/", _page(EV))
    with pytest.raises(RobotsDisallowed):
        get_adapter("jsonld").fetch(fetch_ctx(_unit(), client(transport, tmp_path), settings))


def test_fetch_without_any_json_ld_is_a_format_error(transport: FixtureTransport, settings: Settings, tmp_path: Path):
    transport.add(r"/shows/$", b"<html>redesigned, no markup</html>")
    with pytest.raises(ValueError, match="no JSON-LD"):
        get_adapter("jsonld").fetch(fetch_ctx(_unit(), client(transport, tmp_path), settings))


# ───────────────────────────── real recorded pages ─────────────────────────────

REAL = sorted(
    p.parent.name for p in FIXTURES.glob("*/meta.json") if json.loads(p.read_text()).get("adapter") == "jsonld"
)


def _real(source_id: str) -> Parsed:
    u = real_unit(source_id)
    meta = json.loads((FIXTURES / source_id / "meta.json").read_text())
    payloads = []
    for name, url in meta["files"].items():
        payloads.append((Payload(url, 200, (FIXTURES / source_id / name).read_bytes(), NOW, "html"), None))
    return parse_payloads(get_adapter("jsonld"), u, payloads, NOW)


def test_real_fixtures_exist():
    assert len(REAL) >= 4, REAL


@pytest.mark.parametrize("source_id", REAL)
def test_real_fixture_parses_without_rejects(source_id: str):
    parsed = _real(source_id)
    assert parsed.valid, source_id
    assert not parsed.rejects, parsed.rejects[:3]
    for ev, _ in parsed.valid:
        assert ev.start.tzinfo is not None and ev.category and ev.url is not None
