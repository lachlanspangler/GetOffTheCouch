"""SIDEARM Sports athletics ICS (Washington Huskies) through the generic ``ics`` adapter (real recorded feed)."""

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import unit
from tests.conftest import NOW, fixture_bytes

UW = unit("uw_athletics")


def _parse():
    p = Payload(str(UW.source.params["url"]), 200, fixture_bytes("uw_athletics/payload_0.ics"), NOW, "ics")
    return parse_payloads(get_adapter("ics"), UW, [(p, None)], NOW)


def test_home_games_only_forced_category_no_rejects():
    parsed = _parse()
    assert not parsed.rejects
    titles = sorted(ev.title for ev, _ in parsed.valid)
    # 1 past VEVENT windowed out; 3 away games ("at Purdue", "at UCLA", "at Boise State") skipped, not rejected
    assert parsed.skipped == 3
    assert not any(" at " in t for t in titles)
    assert "Washington Volleyball vs Rutgers - Denim & Dawgs Night" in titles
    # a team schedule: "Softball vs Boise State" is a game to watch, not a rec league to join
    assert {ev.category for ev, _ in parsed.valid} == {"sports_watch.game"}


def test_times_and_all_day_dates():
    evs = {(ev.title, ev.start.date().isoformat()): ev for ev, _ in _parse().valid}
    volley = next(ev for (t, _), ev in evs.items() if t.startswith("Washington Volleyball vs Rutgers"))
    assert volley.start.isoformat() == "2026-10-17T02:00:00+00:00"  # 7 PM PDT on Oct 16
    assert volley.location.address == "Seattle, Wash." and not volley.all_day
    tennis = [ev for (t, _), ev in evs.items() if "ITA Northwest Regionals" in t]
    assert tennis and all(ev.all_day for ev in tennis)  # VALUE=DATE tournament days
