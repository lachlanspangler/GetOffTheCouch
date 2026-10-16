"""Team Trivia venue pages (real pages recorded 2026-10-16, tests/fixtures/teamtrivia_denver)."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from gotc.adapters.base import Payload, get_adapter
from gotc.adapters.common import weekly_occurrences
from gotc.pipeline.ingest import Parsed, parse_payloads
from gotc.settings import Settings
from tests.adapters._util import client, fetch_ctx, unit
from tests.conftest import FIXTURES, NOW, FixtureTransport

MT = ZoneInfo("America/Denver")
DIR = FIXTURES / "teamtrivia_denver"
BASE = "https://www.teamtrivia.com/venue/"


def _parse(*slugs: str, content: dict[str, bytes] | None = None, now: datetime = NOW) -> Parsed:
    u = unit("teamtrivia_denver")
    pl = [
        (Payload(BASE + s, 200, (content or {}).get(s) or (DIR / f"{s}.html").read_bytes(), now, "html"), None)
        for s in slugs
    ]
    return parse_payloads(get_adapter("teamtrivia"), u, pl, now)


def test_venue_page_json_ld_gives_four_reported_dates() -> None:
    parsed = _parse("bruz-beers-denver-co")
    assert parsed.rejects == []
    evs = [ev for ev, _ in parsed.valid]
    assert [ev.start for ev in evs] == [
        datetime(2026, 10, 21, 19, 0, tzinfo=MT),
        datetime(2026, 10, 28, 19, 0, tzinfo=MT),
        datetime(2026, 11, 4, 19, 0, tzinfo=MT),  # after DST ends: still 7 pm local (-07:00 in the JSON-LD)
        datetime(2026, 11, 11, 19, 0, tzinfo=MT),
    ]
    ev = evs[0]
    assert ev.title == "Team Trivia at Bruz Beers"
    assert ev.kind.value == "recurring" and ev.category == "trivia_games.trivia"
    assert ev.recurrence == "Wednesdays 7:00 PM"
    assert ev.price.is_free and ev.availability.value == "free_no_ticket"
    assert ev.location.venue_name == "Bruz Beers"
    assert ev.location.address == "1675 W 67th Ave #100, Denver, CO 80221"
    assert (ev.location.lat, ev.location.lon) == (39.8181295, -105.0073351)
    assert ev.organizer == "Team Trivia"
    assert "303-650-2337" not in ev.model_dump_json()  # the venue phone is never mapped
    assert ev.extras.get("dates") is None  # reported, not derived


def test_two_game_nights_at_one_venue() -> None:
    parsed = _parse("belleview-beer-garden-denver-co")
    assert parsed.rejects == []
    by_game: dict[str, list[datetime]] = {}
    for ev, _ in parsed.valid:
        by_game.setdefault(ev.source_categories[0], []).append(ev.start)
    assert sorted(by_game) == ["Soundcheck Music Bingo", "Team Trivia"]
    assert all(len(v) == 4 for v in by_game.values())
    assert all(d.weekday() == 3 for d in by_game["Team Trivia"])  # Thursdays
    assert all(d.weekday() == 2 for d in by_game["Soundcheck Music Bingo"])  # Wednesdays


def test_json_ld_date_off_the_posted_schedule_is_rejected_not_shown() -> None:
    parsed = _parse("little-machine-beer-denver-co")
    assert len(parsed.rejects) == 1 and "not on the posted schedule (Thursdays)" in parsed.rejects[0][1]
    assert [ev.start.date().isoformat() for ev, _ in parsed.valid] == ["2026-10-22", "2026-10-29", "2026-11-05"]


def test_weekly_table_expands_to_next_four_dates_when_json_ld_has_no_events() -> None:
    raw = (DIR / "bruz-beers-denver-co.html").read_text(encoding="utf-8")
    no_events = re.sub(r'<script type="application/ld\+json">\s*\{"@context":"https://schema.org","@graph".*?</script>',
                       "", raw, flags=re.S)  # fmt: skip
    assert "@graph" not in no_events
    frozen = datetime(2026, 10, 28, 3, 0, tzinfo=UTC)  # Tue Oct 27, 9 pm in Denver
    parsed = _parse("bruz-beers-denver-co", content={"bruz-beers-denver-co": no_events.encode()}, now=frozen)
    assert parsed.rejects == []
    starts = [ev.start for ev, _ in parsed.valid]
    assert starts == [datetime(2026, 10, 28, 19, 0, tzinfo=MT), datetime(2026, 11, 4, 19, 0, tzinfo=MT),
                      datetime(2026, 11, 11, 19, 0, tzinfo=MT), datetime(2026, 11, 18, 19, 0, tzinfo=MT)]  # fmt: skip
    assert all(ev.extras["dates"] == "derived from the weekly schedule" for ev, _ in parsed.valid)


def test_weekly_occurrences_frozen_time() -> None:
    tz = "America/Denver"
    # Wednesday 2026-10-21 at 6 pm local: tonight's 7 pm game is still ahead
    wed_6pm = datetime(2026, 10, 22, 0, 0, tzinfo=UTC)
    assert weekly_occurrences(2, "7:00 PM", tz, wed_6pm, 2)[0] == datetime(2026, 10, 21, 19, 0, tzinfo=MT)
    # 8 pm the same evening: next week
    wed_8pm = datetime(2026, 10, 22, 2, 0, tzinfo=UTC)
    assert weekly_occurrences(2, "7:00 PM", tz, wed_8pm, 1) == [datetime(2026, 10, 28, 19, 0, tzinfo=MT)]
    # wall-clock time survives the DST change (Nov 1)
    got = weekly_occurrences(6, "10:00 AM", tz, wed_8pm, 3)
    assert [d.hour for d in got] == [10, 10, 10] and got[1].utcoffset() != got[0].utcoffset()


def test_fetch_reads_region_page_then_venue_pages(tmp_path: Path, settings: Settings) -> None:
    t = FixtureTransport()
    t.add("teamtrivia.com/robots.txt", (
        "User-agent: *\nDisallow: /getlocation.php\nDisallow: /enter-site.php\nDisallow: /admin/\n"
    ))  # fmt: skip
    t.add(r"/trivia-in-denver/$", (DIR / "trivia-in-denver.html").read_bytes())
    t.add(r"/venue/", (DIR / "bruz-beers-denver-co.html").read_bytes())
    fr = get_adapter("teamtrivia").fetch(fetch_ctx(unit("teamtrivia_denver"), client(t, tmp_path), settings))
    assert len(fr.payloads) == 29 and fr.complete
    assert not any("getlocation" in c or "enter-site" in c for c in t.calls)
