"""Phoenix Public Library: LibCal (Springshare) per-branch iCal subscriptions through the generic ``ics`` adapter
(real recorded feed, tests/fixtures/phoenix_public_library_events)."""

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import unit
from tests.conftest import NOW, fixture_bytes

PPL = unit("phoenix_public_library_events")
URL = "https://calendar.phoenixpubliclibrary.org/ical_subscribe.php?src=p&cid=15413"


def _parse():
    p = Payload(URL, 200, fixture_bytes("phoenix_public_library_events/payload_0.ics"), NOW, "ics")
    return parse_payloads(get_adapter("ics"), PPL, [(p, None)], NOW)


def test_config_lists_every_branch_calendar():
    urls = PPL.source.params["url"]
    assert isinstance(urls, list) and len(urls) == 17 and URL in urls


def test_parses_libcal_feed_without_rejects():
    parsed = _parse()
    assert not parsed.rejects
    assert len(parsed.valid) == 6


def test_branch_location_times_and_categories():
    evs = {ev.title: ev for ev, _ in _parse().valid}
    story = evs["Family Storytime"]
    assert story.start.isoformat() == "2026-10-17T10:00:00-07:00"  # 17:00Z = 10 AM in Phoenix (no DST)
    assert story.location.venue_name is not None and "Burton Barr Central Library" in (
        story.location.venue_name + (story.location.address or "")
    )
    assert story.category == "family.kids"  # "Childrens' Programs, Storytimes" via category_map
    assert evs["Dungeons and Dragons"].category in {"learning.tech", "family.kids"}
    muertos = evs["Día de los Muertos Celebration"]
    assert muertos.all_day  # VALUE=DATE event
