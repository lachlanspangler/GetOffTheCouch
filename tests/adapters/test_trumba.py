"""Trumba JSON adapter against real recorded feeds (Seattle Public Library, University of Washington)."""

import json

import pytest

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import by_id, client, fetch_ctx, parse, unit
from tests.conftest import NOW, FixtureTransport

SPL = unit("spl_events")
UW = unit("uw_events")


def test_real_fixtures_parse_without_rejects():
    for u in (SPL, UW):
        parsed = parse(u, f"{u.source.id}/payload_0.json")
        assert len(parsed.valid) == 5 and not parsed.rejects, u.source.id


def test_spl_field_mapping_and_explicit_offset():
    evs = by_id(parse(SPL, "spl_events/payload_0.json"))
    exhibit = evs["209046621"]
    assert exhibit.title == '"Battle for Paradise: Puerto Rico, restrictions apply*" Exhibit'  # entities unescaped
    assert exhibit.start.isoformat() == "2026-10-17T10:00:00-07:00"  # wall clock + startTimeZoneOffset
    assert exhibit.end is not None and exhibit.end.isoformat() == "2026-10-17T18:00:00-07:00"
    assert exhibit.location.venue_name == "Seattle Public Library – Central Library (Level 8 - Gallery)"
    assert exhibit.kind == "recurring" and exhibit.recurrence == "Every day through December 6, 2026"
    assert exhibit.url is not None and "eventid%3D209046621" in str(exhibit.url)
    assert "registration_required" not in exhibit.tags  # "Registration is not required."
    assert evs["205956788"].availability == "cancelled"
    assert evs["205959256"].category == "family.kids"  # Toddler Play Group


def test_uw_coordinates_from_maps_link_and_all_day_ranges():
    evs = by_id(parse(UW, "uw_events/payload_0.json"))
    show = evs["206158236"]
    assert show.location.lat == pytest.approx(47.658392) and show.location.lon == pytest.approx(-122.306461)
    assert show.location.venue_name == "Art Building (ART) (Jacob Lawrence Gallery)"
    assert show.all_day and show.category == "arts.museum"  # "Event Types: Exhibits" via category_map
    assert show.start.isoformat() == "2026-09-30T00:00:00-07:00"
    teal = evs["209063433"]
    # all-day ends are exclusive midnights: 2027-06-12T00:00 means "through June 11"
    assert teal.end is not None and teal.end.date().isoformat() == "2027-06-11"
    assert teal.organizer == "Tateuchi East Asia Library"  # "Event sponsors" custom field


def test_broken_rows_are_rejected_not_dropped():
    body = [
        {"eventID": 1, "title": "", "startDateTime": "2026-10-20T10:00:00"},
        "nonsense",
        {
            "eventID": 2,
            "title": "Book Club",
            "startDateTime": "2026-10-20T18:00:00",
            "startTimeZoneOffset": "-0700",
            "location": "Ballard Branch",
            "canceled": False,
            "openSignUp": True,
            "reservationFull": True,
            "waitingListAvailable": True,
            "eventActionUrl": "https://www.trumba.com/eventactions/kalendaro#/x",
        },
    ]
    parsed = parse_payloads(
        get_adapter("trumba"), SPL, [(Payload("u", 200, json.dumps(body).encode(), NOW), None)], NOW
    )
    assert len(parsed.rejects) == 2
    club = by_id(parsed)["2"]
    assert club.availability == "waitlist" and club.offers[0].kind == "registration"


def test_fetch_sends_local_startdate_and_days(tmp_path, settings):
    t = FixtureTransport().add(r"trumba\.com/calendars/kalendaro\.json", [])
    fr = get_adapter("trumba").fetch(fetch_ctx(SPL, client(t, tmp_path), settings))
    assert fr.complete and len(fr.payloads) == 1
    url = next(c for c in t.calls if "kalendaro.json" in c)
    assert "startdate=20261015" in url and "days=14" in url  # 2026-10-16T03:00Z is still Oct 15 in Seattle


def test_seattle_city_calendar_skips_government_meetings():
    """seattle.gov's city-wide Trumba calendar (real recorded page): council/committee meetings are skipped by
    the source's exclude_location rule; parks, work parties and markets are kept."""
    parsed = parse(unit("seattle_city_events"), "seattle_city_events/payload_0.json")
    assert not parsed.rejects
    titles = {ev.title for ev, _ in parsed.valid}
    assert parsed.skipped == 3  # School Traffic Safety Committee, Revenue Forecast Council, Select Budget Committee
    assert not any(("Committee" in t or "Council" in t) for t in titles)
    assert {"Open Adoption Hours", "Delridge Farmers Market", "Carkeek STARS Work Party"} <= titles
