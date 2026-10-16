"""San Francisco platform variants against real recorded payloads (batch B onboarding, 2026-10-16).

* ``sf_special_events``: Socrata street closures whose geometry is a GeoJSON LineString (lat/lon taken from the
  first vertex via a dotted path) and whose record id is case number + day (segments of one event collapse).
* ``sf_recpark_events``: a CivicPlus iCalendar feed (``/common/modules/iCalendar/iCalendar.aspx``) through the
  generic ``ics`` adapter.
"""

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import by_id, parse, unit
from tests.conftest import NOW, fixture_bytes


def test_street_closures_map_linestring_coords_and_categories():
    parsed = parse(unit("sf_special_events"), "sf_special_events/payload_0.json")
    assert not parsed.rejects
    evs = by_id(parsed)
    market = evs["1453910:2026-10-16"]
    assert market.title == "Castro Night Market Series 2026"
    assert market.category == "community.market"  # category_rules: "night market"
    assert market.start.isoformat() == "2026-10-16T11:00:00-07:00"  # naive local time, city zone
    assert market.location.lat is not None and 37.70 < market.location.lat < 37.82
    assert market.location.lon is not None and -122.52 < market.location.lon < -122.35
    assert market.location.address == "18TH ST between CASTRO ST and HARTFORD ST"
    assert evs["1522782:2026-10-17"].category == "community.festival"  # "Street Fair"


def test_civicplus_ical_feed_parses_without_rejects():
    u = unit("sf_recpark_events")
    p = Payload(u.source.params["url"][0], 200, fixture_bytes("sf_recpark_events/payload_0.ics"), NOW, "ics")
    parsed = parse_payloads(get_adapter("ics"), u, [(p, None)], NOW)
    assert not parsed.rejects and len(parsed.valid) == 11
    titles = {ev.title for ev, _ in parsed.valid}
    assert "Sunset Dunes Community Cleanup" in titles
    assert not any(t.endswith(" Day") for t in titles)  # holiday markers never become events
    cleanup = next(ev for ev, _ in parsed.valid if ev.title == "Sunset Dunes Community Cleanup")
    assert cleanup.category == "volunteer.one_off"
    assert cleanup.start.isoformat() == "2026-11-08T13:00:00-08:00"  # TZID=America/Los_Angeles, after DST ends
