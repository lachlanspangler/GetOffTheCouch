"""RunSignup Get Races: recorded Chicago response (tests/fixtures/runsignup, 10 of 55 real races)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from gotc.adapters.base import get_adapter
from gotc.config import Registry, load_registry
from gotc.schema import Availability, Method
from gotc.settings import Settings
from tests.adapters._util import by_id, client, fetch_ctx, parse, unit
from tests.conftest import NOW, FixtureTransport, fixture_bytes

CT = ZoneInfo("America/Chicago")
ET = ZoneInfo("America/New_York")


@pytest.fixture
def parsed():  # type: ignore[no-untyped-def]
    return parse(unit("runsignup"), "runsignup/payload_0.json")


def test_real_fixture_has_no_rejects_and_skips_virtual_and_past(parsed) -> None:  # type: ignore[no-untyped-def]
    assert parsed.rejects == []
    ids = {rid.split(":")[0] for rid in by_id(parsed)}
    assert "175729" not in ids  # "Spiked Apple Virtual 5k": every event is virtual_race
    assert "139113" not in ids  # "Life Time Events: Add-On Purchases": next_date 01/01/2026 already passed
    assert len(ids) == 8


def test_race_mapping_times_and_tiers(parsed) -> None:  # type: ignore[no-untyped-def]
    ev = by_id(parsed)["148462:2026-10-25"]
    assert ev.title == "Haunted Halloween Half Marathon & 5km"
    assert ev.category == "fitness.race"
    assert ev.start == datetime(2026, 10, 25, 8, 25, tzinfo=CT)  # earliest event start, race timezone
    assert ev.timezone == "America/Chicago" and not ev.all_day
    assert ev.location.address == "2611 N Cannon Drive, Chicago, IL 60614"
    # cheapest/dearest race_fee over periods still open on 2026-10-16 (5K $64 … half $120 last tier)
    assert (ev.price.min, ev.price.max) == (64.0, 120.0)
    assert ev.price.note == "+ processing fee"
    reg = ev.registration
    assert reg is not None and reg.method == Method.REPORTED and reg.confidence == 1.0
    # registration dates are Eastern Time per the API docs, not the race's zone
    assert reg.opens_at == datetime(2025, 10, 27, 1, 0, tzinfo=ET)
    assert reg.closes_at == datetime(2026, 10, 24, 10, 5, tzinfo=ET)
    assert reg.early_bird_ends_at == datetime(2026, 10, 18, 0, 59, tzinfo=ET)  # $105 → $120 tier
    assert [s.value for s in reg.signup_types] == ["individual"]
    assert reg.evidence and "Oct 24, 2026" in reg.evidence
    assert ev.availability == Availability.REGISTRATION_OPEN
    offer = ev.offers[0]
    assert offer.seller == "RunSignup" and offer.kind.value == "registration"
    assert str(offer.url) == "https://runsignup.com/Race/IL/Chicago/HauntedHalloweenHalf"
    assert offer.price_min == 64.0 and offer.fees_included is False


def test_venue_name_split_from_street(parsed) -> None:  # type: ignore[no-untyped-def]
    ev = by_id(parsed)["47786:2026-11-28"]
    assert ev.location.venue_name == "Christ the King School Gymnasium"
    assert ev.location.address == "9225 S Hamilton Ave, Chicago, IL 60643"
    assert ev.registration and ev.registration.closes_at == datetime(2026, 11, 25, 18, 0, tzinfo=ET)


def test_free_entries_dont_set_the_headline_price(parsed) -> None:  # type: ignore[no-untyped-def]
    ev = by_id(parsed)["6223:2026-11-26"]  # Chi Town Turkey Trot: a $0 kids' division plus paid entries
    assert ev.price.min and ev.price.min > 0 and not ev.price.is_free
    assert ev.price.note and "some entries free" in ev.price.note
    free = by_id(parsed)["194061:2026-10-31"]  # cyclocross: every entry reports $0.00
    assert free.price.is_free


def test_cancellations(parsed) -> None:  # type: ignore[no-untyped-def]
    how = by_id(parsed)["210095:2026-10-18"]  # postponed_cancelled_text says "has been canceled"
    assert how.availability == Availability.CANCELLED
    assert how.description and how.description.startswith("Due to unforeseen circumstances")
    xc = by_id(parsed)["186355:2026-11-29"]  # title starts with CANCELLED (normalize.py)
    assert xc.availability == Availability.CANCELLED


def test_every_registration_is_reported_with_a_close_date(parsed) -> None:  # type: ignore[no-untyped-def]
    regs = [ev.registration for ev, _ in parsed.valid]
    assert all(r is not None and r.closes_at is not None and r.method == Method.REPORTED for r in regs)


def test_fetch_queries_zip_radius_window_and_sends_caller_registration(
    tmp_path: Path, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RUNSIGNUP_API_REG", "reg-token")
    monkeypatch.setenv("RUNSIGNUP_API_REG_SECRET", "reg-secret")
    seen: dict[str, str] = {}
    t = FixtureTransport()
    t.add("runsignup.com/robots.txt", "User-agent: *\nDisallow: /Race/FindARunner/\n")

    def handler(req):  # type: ignore[no-untyped-def]
        import httpx

        seen.update(dict(req.url.params))
        seen["secret"] = req.headers.get("X-RSU-API-REG-SECRET", "")
        return httpx.Response(200, content=fixture_bytes("runsignup/payload_0.json"))

    t.add_fn(r"runsignup\.com/Rest/races", handler)
    u = unit("runsignup")
    assert u.city.slug  # first unit of the global source
    fr = get_adapter("runsignup").fetch(fetch_ctx(u, client(t, tmp_path), settings))
    assert len(fr.payloads) == 1 and fr.complete  # 10 races < results_per_page → one page
    zips = u.source.params["zipcodes"]
    assert seen["zipcode"] == zips[u.city.slug]
    assert seen["start_date"] == NOW.astimezone(ZoneInfo(u.city.timezone)).date().isoformat()
    assert seen["events"] == "T" and seen["format"] == "json" and seen["sort"] == "date ASC"
    assert seen["rsu_api_reg"] == "reg-token" and seen["secret"] == "reg-secret"


def test_unit_is_gated_on_api_caller_registration() -> None:
    reg = load_registry()
    src = reg.all_sources()["runsignup"]
    assert src.scope == "all_cities"
    assert set(src.requires) == {"RUNSIGNUP_API_REG", "RUNSIGNUP_API_REG_SECRET"}
    assert set(src.params["zipcodes"]) == {s for s, c in reg.cities.items() if c.enabled}  # every live city has a ZIP
    assert isinstance(reg, Registry)
