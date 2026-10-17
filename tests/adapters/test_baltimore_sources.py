"""Baltimore (batch A): Enoch Pratt Free Library's iCalendar feed through the generic ``ics`` adapter.

New platform variant: the feed declares ``X-WR-TIMEZONE:Eastern Time (US & Canada)`` (a Rails display name, not an
IANA key). recurring_ical_events raised ZoneInfoNotFoundError on it and the whole feed was lost on the first live run;
``ics._fix_x_wr_timezone`` now maps such names to IANA. Real recorded feed, trimmed to 8 VEVENTs.
"""

import icalendar

from gotc.adapters import ics
from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import unit
from tests.conftest import NOW, fixture_bytes

PRATT = unit("pratt_library_events")


def _parse():
    p = Payload(str(PRATT.source.params["url"]), 200, fixture_bytes("pratt_library_events/payload_0.ics"), NOW, "ics")
    return parse_payloads(get_adapter("ics"), PRATT, [(p, None)], NOW)


def test_rails_x_wr_timezone_no_longer_loses_the_feed():
    parsed = _parse()
    assert not parsed.rejects  # was: 1 reject "parser crashed: ZoneInfoNotFoundError" and 0 valid
    assert len(parsed.valid) == 8
    yoga = next(ev for ev, _ in parsed.valid if ev.title.startswith("Morning Mindfulness"))
    assert yoga.start.isoformat() == "2026-10-16T10:00:00-04:00"  # 14:00Z, shown in X-WR-TIMEZONE (EDT)
    assert yoga.location.venue_name == "Central Library"  # the room ("Creative Arts Center") is split off


def test_x_wr_timezone_mapping():
    def fixed(name: str, city: str = "America/New_York") -> str:
        cal = icalendar.Calendar()
        cal.add("X-WR-TIMEZONE", name)
        ics._fix_x_wr_timezone(cal, city)
        return str(cal["X-WR-TIMEZONE"])

    assert fixed("Eastern Time (US & Canada)") == "America/New_York"
    assert fixed("Central Standard Time") == "America/Chicago"  # Windows name, via icalendar's table
    assert fixed("America/Denver") == "America/Denver"  # valid IANA keys are left alone
    assert fixed("Somewhere Odd", city="America/Chicago") == "America/Chicago"  # unknown → the city's zone
