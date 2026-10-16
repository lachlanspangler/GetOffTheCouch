"""UpcomingCons schema.org Event microdata against real recorded list pages (tests/fixtures/upcomingcons/)."""

import json
from datetime import UTC, datetime

import pytest

from gotc.adapters.base import FetchContext, ParseContext, Payload, get_adapter
from gotc.adapters.upcomingcons import _place
from gotc.config import CityConfig, SourceConfig, Unit
from gotc.pipeline.ingest import parse_payloads
from tests.conftest import FIXTURES, FixtureTransport, fast_client

SRC = SourceConfig(
    id="upcomingcons",
    adapter="upcomingcons",
    name="UpcomingCons",
    data_type="conventions",
    scope="all_cities",
    params={"extra_localities": {"chicago": ["Rosemont", "Schaumburg"]}},
)
CITIES = {
    "minneapolis": CityConfig(
        slug="minneapolis",
        name="Minneapolis",
        state="MN",
        timezone="America/Chicago",
        center=(44.9778, -93.2650),
        aliases=["Mpls", "St. Paul", "Saint Paul", "Bloomington"],
    ),
    "chicago": CityConfig(
        slug="chicago", name="Chicago", state="IL", timezone="America/Chicago", center=(41.88, -87.63)
    ),
    "los_angeles": CityConfig(
        slug="los_angeles",
        name="Los Angeles",
        state="CA",
        timezone="America/Los_Angeles",
        center=(34.05, -118.24),
        aliases=["LA", "Long Beach", "Glendale"],
    ),
    "seattle": CityConfig(
        slug="seattle", name="Seattle", state="WA", timezone="America/Los_Angeles", center=(47.6, -122.3)
    ),
}


def unit(city: str) -> Unit:
    return Unit(source=SRC, city=CITIES[city])


def recorded() -> list[tuple[Payload, None]]:
    meta = json.loads((FIXTURES / "upcomingcons" / "meta.json").read_text())
    at = datetime.fromisoformat(meta["recorded_at"])
    return [
        (Payload(url, 200, (FIXTURES / "upcomingcons" / name).read_bytes(), at, "html"), None)
        for name, url in meta["urls"].items()
    ]


def parsed(city: str):
    pl = recorded()
    return parse_payloads(get_adapter("upcomingcons"), unit(city), pl, pl[0][0].fetched_at)


def research() -> Payload:
    content = (FIXTURES / "upcomingcons" / "research_2026-10-15_anime-cons.html").read_bytes()
    return Payload("https://www.upcomingcons.com/anime-cons", 200, content, datetime(2026, 10, 15, 18, tzinfo=UTC))


@pytest.mark.parametrize(("city", "n"), [("minneapolis", 3), ("chicago", 2), ("los_angeles", 2), ("seattle", 2)])
def test_real_pages_keep_only_the_citys_cons_without_rejects(city, n):
    p = parsed(city)
    assert len(p.valid) == n and not p.rejects
    for ev, _ in p.valid:
        assert ev.all_day and ev.kind.value == "one_off"
        assert ev.category == "niche" or ev.category.startswith("niche.")
        assert ev.location.address and ev.location.address.endswith(CITIES[city].state)
        assert str(ev.url).startswith("https://www.upcomingcons.com/upcomingcons/")


def test_field_mapping_dates_and_tz():
    by = {ev.record_id: ev for ev, _ in parsed("minneapolis").valid}
    mage = by["40549"]
    assert mage.title == "Minneapolis Anime and Gaming Event"
    assert mage.category == "niche.anime_con"  # taxonomy keyword "anime" in the name
    assert mage.start.isoformat() == "2026-10-30T00:00:00-05:00"  # CDT
    assert mage.end is not None and mage.end.isoformat() == "2026-11-01T23:59:00-06:00"  # CST after DST ends
    assert mage.location.address == "Minneapolis, MN"
    assert mage.extras["listing_dates"] == "Oct 30-Nov 1, 2026"
    # no keyword in "AniMinneapolis" → the honest generic parent, not a guess from the listing page
    ani = next(ev for ev in by.values() if ev.title == "AniMinneapolis")
    assert ani.category == "niche" and ani.extras["classified_by"] == "none (generic con)"


def test_extra_localities_and_full_state_names():
    titles = {ev.title: ev for ev, _ in parsed("chicago").valid}
    assert set(titles) == {"Con+Alt+Delete", "Anime Midwest"}  # Rosemont, "Illinois" / "IL"
    assert titles["Anime Midwest"].location.address == "Rosemont, IL"


def test_aliases_count_but_other_states_do_not():
    titles = {ev.title for ev, _ in parsed("los_angeles").valid}
    assert "Anime Los Angeles" in titles  # Long Beach is an alias
    # Glendale is an LA alias, but a Glendale, AZ con must not leak in
    assert all(ev.location.address.endswith(", CA") for ev, _ in parsed("los_angeles").valid)


def test_research_sample():
    p = research()
    evs = list(get_adapter("upcomingcons").parse(p, ParseContext(unit("minneapolis"), p.fetched_at)))
    assert [e["record_id"] for e in evs] == ["40549"]


@pytest.mark.parametrize(
    ("loc", "reg", "expected"),
    [
        ("Minneapolis", "MN", ("Minneapolis", "MN")),
        ("Rosemont", "Illinois", ("Rosemont", "IL")),
        ("San Diego, California", "United States", ("San Diego", "CA")),
        ("Pocatello, Idaho", "USA", ("Pocatello", "ID")),
        ("Manchester", "UK", ("Manchester", None)),
        ("Niagara Falls, ON", "Canada", ("Niagara Falls, ON", None)),
    ],
)
def test_place_normalization(loc, reg, expected):
    assert _place(loc, reg) == expected


def test_fetch_requires_event_markup(settings):
    t = FixtureTransport().add(r"robots\.txt$", "# empty\n").add(r"upcomingcons\.com/", "<html>new layout</html>")
    ctx = FetchContext(
        unit=unit("minneapolis"), http=fast_client(t), now=datetime(2026, 10, 16, tzinfo=UTC), settings=settings
    )
    with pytest.raises(ValueError, match="layout changed"):
        get_adapter("upcomingcons").fetch(ctx)
