"""LibCal branch-calendar ICS (Fresno County Public Library, Clovis branch) through the generic ``ics`` adapter."""

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import unit
from tests.conftest import NOW, fixture_bytes

CLOVIS = unit("fcpl_clovis")


def _parse():
    p = Payload(CLOVIS.source.params["url"], 200, fixture_bytes("fcpl_clovis/payload_0.ics"), NOW, "ics")
    return parse_payloads(get_adapter("ics"), CLOVIS, [(p, None)], NOW)


def test_parses_without_rejects_and_windows_out_past_items():
    parsed = _parse()
    assert not parsed.rejects
    # the feed starts a month back (51 VEVENTs); only items from NOW on survive the window
    assert len(parsed.valid) == 25
    assert all(ev.start >= NOW.replace(hour=0) for ev, _ in parsed.valid)


def test_libcal_categories_drive_the_category_not_the_word_volunteer():
    evs = [ev for ev, _ in _parse().valid]
    homework = next(ev for ev in evs if ev.title == "Clovis: Homework Help")
    assert homework.source_categories == ["Homework Help", "Volunteer-Led"]
    assert homework.category == "family.kids"  # first mapped label wins
    # "Volunteer-Led" programs are led by volunteers; they are not volunteer opportunities
    assert not any(ev.category.startswith("volunteer") for ev in evs)
    story = next(ev for ev in evs if ev.title == "Clovis: Preschool Storytime")
    assert story.category == "family.kids"
    assert story.start.isoformat() == "2026-10-20T10:45:00-07:00"
    assert story.location.venue_name == "Children's Area"  # a room; the build pins it to the branch (fallback_point)
