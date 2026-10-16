"""Galaxy Digital Get Connected (RSS discovery + need detail pages) against real recorded payloads."""

import json
from datetime import UTC, datetime, time

import httpx
import pytest

from gotc.adapters.base import FetchContext, ParseContext, Payload, get_adapter
from gotc.adapters.galaxydigital import _time_range, need_ids_from_rss
from gotc.config import CityConfig, SourceConfig, Unit
from gotc.pipeline.ingest import parse_payloads
from tests.conftest import FIXTURES, FixtureTransport, fast_client

TENANTS = {
    "handson_twin_cities": (
        "minneapolis",
        "Minneapolis",
        "MN",
        "America/Chicago",
        "https://handsontwincities.galaxydigital.com",
    ),
    "uwkc_volunteer": ("seattle", "Seattle", "WA", "America/Los_Angeles", "https://volunteer.uwkc.org"),
}


def unit(sid: str, **params) -> Unit:
    slug, name, state, tz, base = TENANTS[sid]
    src = SourceConfig(
        id=sid,
        adapter="galaxydigital",
        name="HandsOn Twin Cities" if slug == "minneapolis" else "United Way of King County",
        data_type="volunteer",
        params={"base_url": base, **params},
    )
    return Unit(source=src, city=CityConfig(slug=slug, name=name, state=state, timezone=tz, center=(0, 0)))


def payloads(sid: str) -> list[tuple[Payload, None]]:
    meta = json.loads((FIXTURES / sid / "meta.json").read_text())
    at = datetime.fromisoformat(meta["recorded_at"])
    out = []
    for name, url in meta["kept"].items():
        ct = "xml" if name.endswith(".xml") else "html"
        out.append((Payload(url, 200, (FIXTURES / sid / name).read_bytes(), at, ct), None))
    return out


def parsed(sid: str):
    pl = payloads(sid)
    return parse_payloads(get_adapter("galaxydigital"), unit(sid), pl, pl[0][0].fetched_at)


def by_id(sid: str):
    return {ev.record_id: ev for ev, _ in parsed(sid).valid}


@pytest.mark.parametrize(("sid", "n"), [("handson_twin_cities", 11), ("uwkc_volunteer", 7)])
def test_real_fixtures_parse_without_rejects(sid, n):
    p = parsed(sid)
    assert len(p.valid) == n and not p.rejects
    for ev, _ in p.valid:
        assert ev.category.startswith("volunteer.") and ev.price.is_free
        assert ev.offers and ev.offers[0].kind.value == "registration"
        assert str(ev.url).endswith(f"need_id={ev.record_id.split(':')[0]}")


def test_rss_is_discovery_only_and_yields_need_ids_in_order():
    rss = (FIXTURES / "handson_twin_cities" / "payload_0.xml").read_bytes()
    ids = need_ids_from_rss(rss)
    assert len(ids) == 15 and ids[0] == "1330212"
    research = (FIXTURES / "handson_twin_cities" / "research_need-rss_2026-10-15.xml").read_bytes()
    assert need_ids_from_rss(research)[:2] == ["1330212", "1330207"]
    p = Payload("https://x.example/need/rss/", 200, rss, datetime(2026, 10, 16, tzinfo=UTC), "xml")
    assert list(get_adapter("galaxydigital").parse(p, ParseContext(unit("handson_twin_cities"), p.fetched_at))) == []


def test_rss_with_entities_is_refused():
    evil = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa">]><rss><channel><item><link>&a;</link></item></channel></rss>'
    with pytest.raises(ValueError, match="DOCTYPE"):
        need_ids_from_rss(evil)


def test_ongoing_need_is_listed_for_the_fetch_day_only():
    ev = by_id("handson_twin_cities")["1330212"]
    assert ev.title == "Wellness Ally - Exercise Partner"
    assert ev.kind.value == "recurring" and ev.category == "volunteer.recurring" and ev.all_day
    # fetched 2026-10-16 05:03 UTC = 2026-10-16 00:03 in Minneapolis
    assert ev.start.isoformat() == "2026-10-16T00:00:00-05:00"
    assert ev.end is not None and ev.end.isoformat() == "2026-10-16T23:59:00-05:00"
    assert ev.recurrence == "Ongoing"
    assert ev.organizer == "Living Well Disability Services"
    assert ev.registration is not None and ev.registration.closes_at is None
    assert ev.extras["dates_basis"] == "listed as open on the fetch date"


def test_until_sets_end_and_closes_at_extracted():
    ev = by_id("handson_twin_cities")["1330019"]
    assert ev.end is not None and ev.end.isoformat() == "2026-12-18T23:59:00-06:00"  # CST after Nov 1
    reg = ev.registration
    assert reg is not None and reg.closes_at == ev.end
    assert reg.method.value == "extracted" and reg.evidence == "Until Dec 18, 2026"
    assert ev.organizer == "Gifts for Seniors"


def test_register_by_and_virtual_board_role():
    ev = by_id("handson_twin_cities")["1328305"]
    assert ev.category == "volunteer.board"
    assert ev.extras["virtual"] is True and ev.location.address is None
    assert ev.registration is not None and ev.registration.closes_at is not None
    assert ev.registration.closes_at.date().isoformat() == "2026-11-13"
    assert ev.registration.evidence == "Register by Nov 13, 2026"


def test_shift_table_becomes_one_record_per_shift():
    evs = [e for e in by_id("handson_twin_cities").values() if e.record_id.startswith("1328905:")]
    assert len(evs) == 6  # max_shifts default
    first = min(evs, key=lambda e: e.start)
    assert first.start.isoformat() == "2026-10-16T09:30:00-05:00"
    assert first.end is not None and first.end.isoformat() == "2026-10-16T11:15:00-05:00"
    assert not first.all_day
    assert first.extras["spots_left"] == 30 and first.extras["spots_total"] == 30
    assert first.availability.value == "registration_open"
    assert first.location.address == "18732 Lake Drive East, Chanhassen, MN 55317"
    assert {"family_friendly", "accessible"} <= set(first.tags)
    assert first.registration is not None
    assert [s.value for s in first.registration.signup_types] == ["individual", "team"]


def test_seattle_dates_times_and_tz():
    by = by_id("uwkc_volunteer")
    wrap = by["1326690"]  # "Happens On Dec 12, 2026" + "10:00am - 12:30 (estimated)"
    assert wrap.start.isoformat() == "2026-12-12T10:00:00-08:00"
    assert wrap.end is not None and wrap.end.isoformat() == "2026-12-12T12:30:00-08:00"
    assert not wrap.all_day
    adv = by["1326674"]  # "4:30-6:00 pm", "Register by Nov 3, 2026"
    assert adv.start.time() == time(16, 30) and adv.end is not None and adv.end.time() == time(18, 0)
    assert adv.registration is not None and adv.registration.closes_at is not None
    assert adv.registration.closes_at.isoformat() == "2026-11-03T23:59:00-08:00"
    choir = by["1321980"]  # "Oct 16, 2026 through Oct 17, 2026", two time ranges → stays all-day
    assert choir.all_day and choir.start.date().isoformat() == "2026-10-16"
    assert choir.end is not None and choir.end.date().isoformat() == "2026-10-17"
    past = by["1323425"]  # "Register by Oct 14, 2026", fetched Oct 15 (Pacific)
    assert past.availability.value == "registration_closed"
    assert past.offers[0].availability.value == "registration_closed"
    assert all(e.timezone == "America/Los_Angeles" for e in by.values())


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("9am-1pm", (time(9), time(13))),
        ("10-12:30pm", (time(10), time(12, 30))),
        ("4:30-6:00 pm", (time(16, 30), time(18))),
        ("Shifts between: 2:30pm - 9pm", (time(14, 30), time(21))),
        ("10:00am - 12:30 (estimated)", (time(10), time(12, 30))),
        ("12:45- 4:00 pm or 6:15-9:00 pm", (None, None)),
        ("Flexible", (None, None)),
        ("Varied, see description", (None, None)),
    ],
)
def test_time_range_text(text, expected):
    assert _time_range(text) == expected


def test_fetch_reads_rss_then_detail_pages_and_skips_gone_needs(settings):
    rss = (FIXTURES / "handson_twin_cities" / "payload_0.xml").read_bytes()
    page = (FIXTURES / "handson_twin_cities" / "payload_1.html").read_bytes()

    def detail(req: httpx.Request) -> httpx.Response:
        return httpx.Response(404 if req.url.params.get("need_id") == "1330207" else 200, content=page)

    t = (
        FixtureTransport()
        .add(r"robots\.txt$", "User-agent: BLEXBot\nDisallow: /\n\nUser-agent: *\nDisallow:\n")
        .add(r"/need/rss/", rss)
        .add_fn(r"/need/detail/", detail)
    )
    now = datetime(2026, 10, 16, 5, 0, tzinfo=UTC)
    ctx = FetchContext(unit=unit("handson_twin_cities", max_details=3), http=fast_client(t), now=now, settings=settings)
    fr = get_adapter("galaxydigital").fetch(ctx)
    assert [p.content_type for p in fr.payloads] == ["xml", "html", "html"]  # 1330207 → 404 → skipped
    assert not fr.complete  # a 15-newest window: never mark the rest gone
