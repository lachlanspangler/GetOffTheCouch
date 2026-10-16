"""Challenge Entertainment show finder JSON (real objects recorded 2026-10-16, tests/fixtures/challenge_trivia)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from tests.adapters._util import parse, unit

FIX = "challenge_trivia/payload_0.json"
CT = ZoneInfo("America/Chicago")


def test_austin_weekly_shows_expand_to_four_dates() -> None:
    parsed = parse(unit("challenge_trivia_austin"), FIX)
    assert parsed.rejects == []
    celis = sorted((ev for ev, _ in parsed.valid if ev.record_id.startswith("169888:")), key=lambda e: e.start)
    assert [ev.start for ev in celis] == [
        datetime(2026, 10, 19, 19, 0, tzinfo=CT),
        datetime(2026, 10, 26, 19, 0, tzinfo=CT),
        datetime(2026, 11, 2, 19, 0, tzinfo=CT),  # wall-clock 7 pm after DST ends
        datetime(2026, 11, 9, 19, 0, tzinfo=CT),
    ]
    ev = celis[0]
    assert ev.title == "Live Trivia at Celis Brewery - North Austin"
    assert ev.kind.value == "recurring" and ev.category == "trivia_games.trivia"
    assert ev.recurrence == "Weekly · Mondays 7:00 PM"
    assert ev.location.address == "10001 Metric Blvd, Austin, TX 78758" and ev.location.lat is not None
    assert ev.extras["dates"] == "reported (next_date)"
    assert celis[1].extras["dates"] == "derived: next_date + 7 days"
    assert "phone" not in ev.model_dump_json().lower()


def test_metro_and_distance_filters() -> None:
    ids = {ev.record_id.split(":")[0] for ev, _ in parse(unit("challenge_trivia_austin"), FIX).valid}
    assert ids == {"169888", "169930", "160434", "169942"}  # Killeen (~95 km) and other metros left out


def test_bi_weekly_steps_fourteen_days() -> None:
    parsed = parse(unit("challenge_trivia_austin"), FIX)
    mueller = sorted(ev.start.date() for ev, _ in parsed.valid if ev.record_id.startswith("169942:"))
    assert mueller == [date(2026, 10, 22), date(2026, 11, 5), date(2026, 11, 19), date(2026, 12, 3)]


def test_nashville_bingo_category_and_suburbs() -> None:
    parsed = parse(unit("challenge_trivia_nashville"), FIX)
    assert parsed.rejects == []
    cats = {ev.record_id.split(":")[0]: ev.category for ev, _ in parsed.valid}
    assert cats["171013"] == "trivia_games.bingo"  # Xtreme Bar Bingo (Franklin)
    assert cats["171033"] == "trivia_games.trivia"  # The Pub – The Gulch
    assert "170989" in cats  # Murfreesboro is ~50 km out: inside 2× the 25 km radius


def test_day_mismatch_trusts_next_date_and_does_not_expand() -> None:
    u = unit("challenge_trivia_austin", metros=["houston"], max_km=1000)
    parsed = parse(u, FIX)
    evs = [ev for ev, _ in parsed.valid if ev.record_id.startswith("170505:")]
    assert len(evs) == 1 and evs[0].start.date() == date(2026, 10, 21)
    assert evs[0].extras["day_mismatch"] is True


def test_monthly_show_only_gets_next_date() -> None:
    u = unit("challenge_trivia_austin", metros=["milwaukee"], max_km=2000)
    evs = [ev for ev, _ in parse(u, FIX).valid]
    assert [ev.start.date() for ev in evs] == [date(2026, 10, 16)]
