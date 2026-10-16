"""Volo Sports discover pages against real recorded fixtures (tests/fixtures/volo_<city>/, see meta.json)."""

import json
from datetime import UTC, date, datetime, timedelta

import pytest

from gotc.adapters.base import FetchContext, ParseContext, Payload, get_adapter
from gotc.adapters.common import infer_year
from gotc.config import CityConfig, SourceConfig, Unit
from gotc.pipeline.ingest import parse_payloads
from tests.conftest import FIXTURES, FixtureTransport, fast_client

CITIES = {
    "volo_denver": ("denver", "Denver", "CO", "America/Denver", "denver"),
    "volo_boston": ("boston", "Boston", "MA", "America/New_York", "boston"),
    "volo_los_angeles": ("los_angeles", "Los Angeles", "CA", "America/Los_Angeles", "los-angeles"),
    "volo_miami": ("miami", "Miami", "FL", "America/New_York", "miami"),
    "volo_nyc": ("nyc", "New York City", "NY", "America/New_York", "new-york-metro-area"),
}


def unit(sid: str, **params) -> Unit:
    slug, name, state, tz, volo_slug = CITIES[sid]
    src = SourceConfig(
        id=sid, adapter="volo", name="Volo", data_type="leagues", params={"city_slug": volo_slug, **params}
    )
    city = CityConfig(slug=slug, name=name, state=state, timezone=tz, center=(0, 0), sources=[src])
    return Unit(source=src, city=city)


def recorded(sid: str, i: int = 0) -> Payload:
    meta = json.loads((FIXTURES / sid / "meta.json").read_text())
    at = datetime.fromisoformat(meta["recorded_at"])
    name = f"payload_{i}.html"
    return Payload(meta["urls"][name], 200, (FIXTURES / sid / name).read_bytes(), at, "html")


def research(at: datetime = datetime(2026, 10, 16, 4, 40, tzinfo=UTC)) -> Payload:
    content = (FIXTURES / "volo_denver" / "research_2026-10-15.html").read_bytes()
    return Payload("https://www.volosports.com/discover/denver?category=leagues", 200, content, at, "html")


def parse(sid: str, p: Payload):
    return parse_payloads(get_adapter("volo"), unit(sid), [(p, None)], p.fetched_at)


def by_id(parsed):
    return {ev.record_id: ev for ev, _ in parsed.valid}


@pytest.mark.parametrize(
    ("sid", "page", "n"),
    [
        ("volo_boston", 0, 24),
        ("volo_denver", 0, 24),
        ("volo_los_angeles", 0, 24),
        ("volo_miami", 0, 17),
        ("volo_nyc", 0, 24),
        ("volo_nyc", 1, 24),
    ],
)
def test_real_fixtures_parse_without_rejects(sid, page, n):
    parsed = parse(sid, recorded(sid, page))
    assert len(parsed.valid) == n and not parsed.rejects
    for ev, _ in parsed.valid:
        assert ev.category.startswith("sports_league.")
        assert ev.title.startswith("Volo ")
        assert ev.offers and ev.offers[0].seller == "Volo" and ev.offers[0].kind.value == "registration"
        assert ev.offers[0].listing_count is None
        assert str(ev.offers[0].url).startswith("https://www.volosports.com/l/")
        assert ev.start.tzinfo is not None and ev.start >= p_date(recorded(sid, page)) - timedelta(days=60)


def p_date(p: Payload) -> datetime:
    return p.fetched_at


def test_nyc_pages_do_not_overlap():
    a = by_id(parse("volo_nyc", recorded("volo_nyc", 0)))
    b = by_id(parse("volo_nyc", recorded("volo_nyc", 1)))
    assert not set(a) & set(b)


def test_field_mapping_on_research_sample():
    ev = by_id(parse("volo_denver", research()))["07259bbb-1c62-4740-b632-6e0885935279"]
    assert ev.title == "Volo Rec/Int Pickleball — RiNo (Sun)"
    assert ev.kind.value == "season" and ev.category == "sports_league.pickleball"
    # 11/8 has no year → next occurrence after the 2026-10-15 (Denver) fetch; MST after Nov 1
    assert ev.start.isoformat() == "2026-11-08T09:00:00-07:00"
    assert ev.end is not None and ev.end.isoformat() == "2026-11-08T12:00:00-07:00"
    assert ev.recurrence == "Sundays · 8 weeks · 9 AM–12 PM"
    assert ev.location.venue_name == "Volo Sports Arena" and ev.location.neighborhood == "RiNo"
    assert (ev.price.min, ev.price.max, ev.price.note) == (79.0, 89.0, "per player; $237/team")
    reg = ev.registration
    assert reg is not None
    assert reg.closes_at is not None and reg.closes_at.isoformat() == "2026-11-06T23:59:00-07:00"
    # "Price goes up 10/17" → early bird ends at the start of 10/17, local (still MDT)
    assert reg.early_bird_ends_at is not None and reg.early_bird_ends_at.isoformat() == "2026-10-17T00:00:00-06:00"
    assert reg.method.value == "extracted" and "Closes 11/6" in (reg.evidence or "")
    assert [s.value for s in reg.signup_types] == ["individual", "team"]
    assert [s.value for s in reg.skill_levels] == ["recreational", "intermediate"]  # "Skills (2)" + "Rec/Int"
    assert ev.availability.value == "registration_open"
    assert {"early_bird", "team_signup"} <= set(ev.tags) and "21+" not in ev.tags
    assert ev.extras["year_inferred"] is True and ev.extras["first_game_raw"] == "11/8"


def test_relative_close_is_fetch_time_plus_delta():
    p = research()
    ev = by_id(parse("volo_denver", p))["c9e481c8-9da4-4153-92f6-1a2fee8db784"]
    assert ev.registration is not None
    assert ev.registration.closes_at == p.fetched_at + timedelta(hours=2, minutes=17)
    assert ev.registration.evidence == "Closing in 2h 17m"
    assert ev.price.min == ev.price.max == 77.0 and ev.price.note == "per player; $385/team"
    # "Upper Int/Comp" with "Skills (2)": both levels named in the title
    assert [s.value for s in ev.registration.skill_levels] == ["intermediate", "competitive"]


def test_party_pickleball_social_beginner_is_beginner_friendly():
    ev = by_id(parse("volo_denver", research()))["f8d81372-00b4-4ee3-817a-64c65dd9f17a"]
    assert ev.registration is not None and [s.value for s in ev.registration.skill_levels] == ["beginner"]
    assert "beginner_friendly" in ev.tags


def test_year_inference_when_fetched_after_the_date():
    # Fetched 2026-12-20: "11/8" (shown as a Sunday) is not next year's 11/8 (a Monday) but this season's,
    # which started 42 days ago — the weekday check keeps it in 2026.
    late = research(datetime(2026, 12, 20, 18, 0, tzinfo=UTC))
    ev = by_id(parse("volo_denver", late))["07259bbb-1c62-4740-b632-6e0885935279"]
    assert ev.start.date() == date(2026, 11, 8)
    # "Closes 11/6" alone would roll to 2027 — but a deadline can't follow the first game, so it's this season's
    assert ev.registration is not None and ev.registration.closes_at is not None
    assert ev.registration.closes_at.date() == date(2026, 11, 6)
    assert ev.registration.early_bird_ends_at is not None and ev.registration.early_bird_ends_at.year == 2026
    assert ev.availability.value == "registration_closed"


def test_infer_year_rules():
    ref = date(2026, 12, 20)
    assert infer_year(1, 10, ref) == date(2027, 1, 10)  # next occurrence on/after the fetch date
    assert infer_year(12, 20, ref) == date(2026, 12, 20)
    assert infer_year(11, 8, ref, weekday=6) == date(2026, 11, 8)  # recent past matching the shown weekday
    assert infer_year(2, 30, ref) is None


def test_los_angeles_statuses_and_tz():
    p = recorded("volo_los_angeles")
    evs = [ev for ev, _ in parse("volo_los_angeles", p).valid]
    assert all(ev.timezone == "America/Los_Angeles" for ev in evs)
    sold = [ev for ev in evs if ev.availability.value == "sold_out"]
    assert len(sold) == 2
    assert all(ev.registration and "free_agent" in [s.value for s in ev.registration.signup_types] for ev in sold)
    last = [ev for ev in evs if ev.extras.get("price_tier") == "last chance"]
    assert last and all(ev.availability.value in ("few_left", "sold_out", "limited") for ev in last)
    spots = {ev.extras["team_spots_left"] for ev in evs if ev.extras.get("team_spots_left") is not None}
    assert spots == {1, 2, 3}
    one = next(ev for ev in evs if ev.extras.get("team_spots_left") == 1)
    assert one.availability.value == "few_left"
    closing = [ev for ev in evs if ev.extras.get("status_text") and "Closing in 1h 52m" in ev.extras["status_text"]]
    assert closing and all(
        ev.registration and ev.registration.closes_at == p.fetched_at + timedelta(hours=1, minutes=52) for ev in closing
    )
    # includeFees pages say so in the price note and on the offer
    assert all(ev.price.note and "incl. fees" in ev.price.note for ev in evs if ev.price.min)
    assert all(ev.offers[0].fees_included for ev in evs)
    mon = next(ev for ev in evs if ev.extras["volo_title"] == "Monday - Coed Basketball - Culver City")
    assert mon.start.utcoffset() == timedelta(hours=-7)  # PDT in October


def test_miami_title_layout_and_stated_season_year():
    evs = [ev for ev, _ in parse("volo_miami", recorded("volo_miami")).valid]
    bocce = next(ev for ev in evs if ev.extras["volo_title"].startswith("Bocce"))
    assert bocce.title == "Volo Bocce (Coed) — Coconut Grove (Thu)"
    assert bocce.category == "sports_league.other"
    assert bocce.extras["year_inferred"] is False  # "- November 2026" is in the title
    corn = next(ev for ev in evs if ev.extras["volo_title"].startswith("Cornhole"))
    assert corn.category == "sports_league.cornhole"


def test_boston_team_spots_left_is_limited():
    evs = [ev for ev, _ in parse("volo_boston", recorded("volo_boston")).valid]
    three = next(ev for ev in evs if ev.extras.get("team_spots_left") == 3)
    assert three.availability.value == "limited"
    assert "indoor" in three.tags


def test_parse_is_pure():
    a = list(get_adapter("volo").parse(research(), ParseContext(unit("volo_denver"), research().fetched_at)))
    b = list(get_adapter("volo").parse(research(), ParseContext(unit("volo_denver"), research().fetched_at)))
    assert a == b


def test_fetch_pages_without_page1_param_and_stops_on_repeat(settings):
    nyc0 = (FIXTURES / "volo_nyc" / "payload_0.html").read_bytes()
    nyc1 = (FIXTURES / "volo_nyc" / "payload_1.html").read_bytes()
    seen: list[str] = []

    def page(req):
        import httpx

        seen.append(str(req.url))
        n = req.url.params.get("page")
        return httpx.Response(200, content=nyc1 if n == "2" else nyc0)

    t = FixtureTransport().add(r"robots\.txt$", "User-agent: *\nDisallow: /admin\n").add_fn(r"/discover/", page)
    u = unit("volo_nyc", include_fees=True, max_pages=6)
    ctx = FetchContext(unit=u, http=fast_client(t), now=datetime(2026, 10, 16, 5, 0, tzinfo=UTC), settings=settings)
    fr = get_adapter("volo").fetch(ctx)
    assert len(fr.payloads) == 2  # page 3 returned page-1 cards again → stop, don't store duplicates
    assert not fr.complete  # 48 of 123 "ways to play" → never mark the rest gone
    assert "page=" not in seen[0] and "includeFees=true" in seen[0]
    assert "page=2" in seen[1]


def test_fetch_rejects_layout_change(settings):
    t = FixtureTransport().add(r"robots\.txt$", "").add(r"/discover/", "<html>maintenance</html>")
    ctx = FetchContext(
        unit=unit("volo_denver"), http=fast_client(t), now=datetime(2026, 10, 16, tzinfo=UTC), settings=settings
    )
    with pytest.raises(ValueError, match="layout changed"):
        get_adapter("volo").fetch(ctx)
