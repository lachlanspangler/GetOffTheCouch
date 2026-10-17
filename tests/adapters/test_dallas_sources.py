"""Dallas (batch A): CivicPlus iCalendar export (Dallas Park & Recreation) through the generic ``ics`` adapter.

CivicPlus is a new platform variant for us: ``/common/modules/iCalendar/iCalendar.aspx?catID=N&feed=calendar``
with a VTIMEZONE block and TZID-qualified DTSTARTs, plus all-day ``VALUE=DATE`` items. Real recorded feed, trimmed
to the 8 soonest VEVENTs.
"""

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import unit
from tests.conftest import NOW, fixture_bytes

PARKS = unit("dallas_parks_events")


def _parse():
    url = str(PARKS.source.params["url"][0])
    p = Payload(url, 200, fixture_bytes("dallas_parks_events/payload_0.ics"), NOW, "ics")
    return parse_payloads(get_adapter("ics"), PARKS, [(p, None)], NOW)


def test_civicplus_ics_parses_without_rejects_and_skips_board_meetings():
    parsed = _parse()
    assert not parsed.rejects
    titles = {ev.title for ev, _ in parsed.valid}
    assert "Goat Yoga @ Harwood Park" in titles
    assert not any("Board Meeting" in t for t in titles)
    assert parsed.skipped == 1  # "Park Board Meeting" (governance) via exclude_location


def test_tzid_times_and_all_day_items():
    evs = {ev.title: ev for ev, _ in _parse().valid}
    yoga = evs["Goat Yoga @ Harwood Park"]
    assert yoga.start.isoformat() == "2026-10-17T10:00:00-05:00"  # TZID=America/Chicago wall time (CDT)
    assert not yoga.all_day
    fest = evs["Fall Festival at Bachman Recreation Center"]
    assert fest.all_day and fest.start.date().isoformat() == "2026-10-22"
