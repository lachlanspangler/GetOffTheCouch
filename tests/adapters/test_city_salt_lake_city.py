"""Now Playing Utah's WordPress (apollo) calendar-subscription ICS through the generic ``ics`` adapter.

Variant: floating local times (no TZID, X-WR-TIMEZONE America/Boise), a statewide feed narrowed to the Salt Lake
area by an ``exclude_location`` allowlist (negative lookahead), DTEND == DTSTART. Real recorded payload, trimmed.
"""

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import unit
from tests.conftest import NOW, fixture_bytes

NPU = unit("now_playing_utah")


def _parse():
    p = Payload(str(NPU.source.params["url"]), 200, fixture_bytes("now_playing_utah/payload_0.ics"), NOW, "ics")
    return parse_payloads(get_adapter("ics"), NPU, [(p, None)], NOW)


def test_only_salt_lake_area_inside_horizon():
    parsed = _parse()
    assert not parsed.rejects
    titles = sorted(ev.title for ev, _ in parsed.valid)
    assert titles == ["Fruit Bats", "Sammy Rae & The Friends with special guest Melt", "Witches Night Out"]
    assert parsed.skipped == 2  # Provo and Ogden are skipped (counted), not rejected; Jan 2027 is past the horizon


def test_floating_times_are_city_local():
    ev = next(ev for ev, _ in _parse().valid if ev.title == "Fruit Bats")
    assert ev.start.isoformat() == "2026-10-16T20:00:00-06:00"  # 8 PM MDT
    assert ev.location.address and ev.location.address.endswith("Salt Lake City, UT 84115")
    assert str(ev.url).startswith("https://nowplayingutah.com/event/")
