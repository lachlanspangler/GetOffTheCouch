"""Batch C platform variants (real recorded payloads, trimmed): LibCal public-calendar ICS, date-only Event JSON-LD,
and a Socrata openings mapping with a SoQL-concatenated street line and MM/DD/YYYY text dates."""

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import Parsed, parse_payloads
from tests.adapters._util import unit
from tests.conftest import NOW, fixture_bytes


def _parse(source_id: str, rel: str, kind: str) -> Parsed:
    u = unit(source_id)
    p = Payload("https://example.test/fixture", 200, fixture_bytes(rel), NOW, kind)
    return parse_payloads(get_adapter(u.source.adapter), u, [(p, None)], NOW)


def test_libcal_ics_windows_out_past_events_and_keeps_local_times() -> None:
    parsed = _parse("heights_libraries_events", "heights_libraries_events/payload_0.ics", "ics")
    assert not parsed.rejects
    # the feed starts ~30 days back (LibCal's 500-event cap); the 2 September VEVENTs are windowed out
    assert len(parsed.valid) == 6
    starts = sorted(ev.start for ev, _ in parsed.valid)
    assert starts[0].isoformat() == "2026-10-17T10:00:00-04:00"
    assert all(not ev.all_day for ev, _ in parsed.valid)
    story = next(ev for ev, _ in parsed.valid if ev.title == "Story Stop")
    assert story.location is not None and story.location.address and "Lee Road" in story.location.address


def test_date_only_jsonld_becomes_all_day_with_venue_address() -> None:
    parsed = _parse("headliners_louisville", "headliners_louisville/payload_0.html", "html")
    assert not parsed.rejects and len(parsed.valid) == 5
    evs = {ev.title: ev for ev, _ in parsed.valid}
    failure = evs["Failure w/ Special Guests Quannnic - THE RISING SKYLINE TOUR"]
    assert failure.all_day and failure.start.date().isoformat() == "2026-10-17"
    assert failure.location is not None
    assert failure.location.address == "1386 Lexington Rd, Louisville, KY 40206"


def test_missouri_new_liquor_licenses_mapping() -> None:
    parsed = _parse("mo_new_liquor_licenses_stl", "mo_new_liquor_licenses_stl/payload_0.json", "json")
    assert not parsed.rejects and len(parsed.valid) == 5
    evs = {ev.record_id: ev for ev, _ in parsed.valid}
    bar = evs["307219"]
    assert bar.title == "Play Time Sports Bar — new liquor license"
    assert bar.kind == "opening" and bar.category == "nightlife.opening"
    assert bar.start.date().isoformat() == "2026-10-07" and bar.all_day  # "10/07/2026" text date, local
    assert bar.location is not None and bar.location.address == "7023 S BROADWAY, SAINT LOUIS"
    assert bar.description and bar.description.startswith("License signal, not a confirmed opening date")
