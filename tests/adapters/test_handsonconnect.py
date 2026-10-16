"""HandsOn Connect calendar JSON against real recorded payloads (Boston Cares, Hands On Nashville)."""

import json
from datetime import UTC, datetime
from urllib.parse import parse_qs

import httpx
import pytest

from gotc.adapters.base import FetchContext, ParseContext, Payload, get_adapter
from gotc.config import CityConfig, SourceConfig, Unit
from gotc.pipeline.ingest import parse_payloads
from tests.conftest import FIXTURES, FixtureTransport, fast_client

TENANTS = {
    "boston_cares": ("boston", "Boston", "MA", "America/New_York", "https://www.bostoncares.org", 589),
    "hands_on_nashville": (
        "nashville",
        "Nashville",
        "TN",
        "America/Chicago",
        "https://handson.unitedwaygreaternashville.org",
        2009,
    ),
}
ENDPOINT = "/search/getOpportunitiesCalendar"


def unit(sid: str, **params) -> Unit:
    slug, name, state, tz, base, block = TENANTS[sid]
    src = SourceConfig(
        id=sid,
        adapter="handsonconnect",
        name=sid.replace("_", " ").title(),
        data_type="volunteer",
        params={"base_url": base, "block_id": block, **params},
    )
    return Unit(source=src, city=CityConfig(slug=slug, name=name, state=state, timezone=tz, center=(0, 0)))


def payload(sid: str, name: str = "payload_0.json") -> Payload:
    meta = json.loads((FIXTURES / sid / "meta.json").read_text())
    at = datetime.fromisoformat(meta.get("recorded_at", "2026-10-15T14:00:00+00:00"))
    return Payload(TENANTS[sid][4] + ENDPOINT, 200, (FIXTURES / sid / name).read_bytes(), at, "json")


def parse(sid: str, p: Payload):
    return parse_payloads(get_adapter("handsonconnect"), unit(sid), [(p, None)], p.fetched_at)


@pytest.mark.parametrize(("sid", "n"), [("boston_cares", 65), ("hands_on_nashville", 80)])
def test_real_fixtures_parse_without_rejects(sid, n):
    parsed = parse(sid, payload(sid))
    assert len(parsed.valid) == n and not parsed.rejects
    for ev, _ in parsed.valid:
        assert ev.category == "volunteer.one_off" and ev.kind.value == "one_off"
        assert ev.price.is_free  # volunteering is free (normalize, I-015)
        assert ev.offers and ev.offers[0].kind.value == "registration"
        assert ev.registration is not None and ev.registration.closes_at is None  # never invented
        assert ev.start.tzinfo is not None and ev.end is not None and ev.end >= ev.start


def test_nashville_campaign_banners_are_not_records_and_tz_is_central():
    parsed = parse("hands_on_nashville", payload("hands_on_nashville"))
    assert not any(ev.title == "Season of Sharing" for ev, _ in parsed.valid)
    ev = next(e for e, _ in parsed.valid if e.record_id == "a0aVN00001hD6xaYAC")
    assert ev.title == "45th Annual Education Pow Wow: Food Booth"
    assert ev.start.isoformat() == "2026-10-16T08:15:00-05:00"
    assert ev.timezone == "America/Chicago"
    assert "Arts & Culture" in ev.source_categories
    assert ev.extras["spots_left"] == 1 and ev.availability.value == "few_left"


def test_field_mapping_on_research_sample():
    p = payload("boston_cares", "research_2026-10-15.json")
    by = {ev.record_id: ev for ev, _ in parse("boston_cares", p).valid}
    assert len(by) == 5
    full = by["a0CUq00007LI7lbMAD"]
    assert full.title == "Serve Breakfast at the Boston Living Center"
    assert full.start.isoformat() == "2026-10-15T07:45:00-04:00"
    assert full.end is not None and full.end.isoformat() == "2026-10-15T10:30:00-04:00"
    assert full.organizer == "Victory Programs - Boston Living Center"
    assert str(full.url) == "https://www.bostoncares.org/opportunity/a0CUq00007LI7lbMAD"
    assert full.location.address == "Back Bay, MA 02116"
    # 0 still needed = full; HOC then offers "Add to Waiting list"
    assert full.availability.value == "waitlist" and full.offers[0].availability.value == "waitlist"
    assert full.extras["spots_left"] == 0 and full.extras["max_attendance"] is None  # "None" string → null
    assert full.offers[0].seller == "Boston Cares"
    two = by["a0CUq00007V00JtMAJ"]
    assert two.title.startswith("Organize and Distribute Food at Catholic Charities' ")  # &#39; unescaped
    assert two.availability.value == "few_left"
    assert by["a0CUq00007LGrk5MAD"].availability.value == "registration_open"  # 3 spots


def test_description_location_line_beats_neighborhood_zip():
    ev = next(e for e, _ in parse("boston_cares", payload("boston_cares")).valid if "Union Square Farmers" in e.title)
    assert ev.location.venue_name == "Union Square Plaza"
    assert ev.location.address == "66-70 Union Square, Somerville, MA 02143"


def test_parse_is_pure():
    p = payload("boston_cares")
    a = list(get_adapter("handsonconnect").parse(p, ParseContext(unit("boston_cares"), p.fetched_at)))
    b = list(get_adapter("handsonconnect").parse(p, ParseContext(unit("boston_cares"), p.fetched_at)))
    assert a == b


def _ctx(settings, t, sid="boston_cares", **params):
    now = datetime(2026, 10, 16, 3, 0, tzinfo=UTC)  # 2026-10-15 23:00 in Boston
    return FetchContext(unit=unit(sid, **params), http=fast_client(t), now=now, settings=settings)


def test_fetch_posts_small_windows_bounded_by_horizon(settings):
    forms: list[dict[str, list[str]]] = []
    body = (FIXTURES / "boston_cares" / "payload_0.json").read_bytes()

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "POST"
        forms.append(parse_qs(req.content.decode()))
        return httpx.Response(200, content=body)

    t = FixtureTransport().add(r"robots\.txt$", status=404).add_fn(ENDPOINT, handler)
    fr = get_adapter("handsonconnect").fetch(_ctx(settings, t, horizon_days=5, window_days=2))
    windows = [(f["searchvo_startfrom"][0], f["searchvo_endfrom"][0]) for f in forms]
    # local date in Boston is still 10/15 at 03:00 UTC
    assert windows == [("2026-10-15", "2026-10-16"), ("2026-10-17", "2026-10-18"), ("2026-10-19", "2026-10-19")]
    assert all(f["searchvo_searchresultblockid"] == ["589"] for f in forms)
    assert len(fr.payloads) == 3 and fr.complete


def test_window_is_capped_at_three_days_and_truncation_is_incomplete(settings):
    forms: list[dict[str, list[str]]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        forms.append(parse_qs(req.content.decode()))
        return httpx.Response(
            200, json={"code": 200, "items": [{"dayDate": "2026-10-15", "overMaxToReturn": "True", "occurrences": []}]}
        )

    t = FixtureTransport().add_fn(ENDPOINT, handler)
    fr = get_adapter("handsonconnect").fetch(_ctx(settings, t, horizon_days=3, window_days=10))
    assert len(forms) == 1 and forms[0]["searchvo_endfrom"] == ["2026-10-17"]
    assert not fr.complete


def test_error_payload_is_a_format_failure(settings):
    msg = {"message": "The StartFrom or EndFrom are invalid dates", "code": 400}
    t = FixtureTransport().add(ENDPOINT, msg)
    with pytest.raises(ValueError, match="invalid dates"):
        get_adapter("handsonconnect").fetch(_ctx(settings, t))
