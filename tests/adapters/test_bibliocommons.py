"""BiblioCommons events RSS adapter against real recorded feeds (Hennepin County Library, Boston Public Library)."""

import httpx
import pytest

from gotc.adapters.base import Payload, get_adapter
from gotc.adapters.bibliocommons import safe_xml
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import by_id, client, dump, fetch_ctx, parse, unit
from tests.conftest import NOW, FixtureTransport, fixture_bytes

HCLIB = unit("hclib_events")
BPL = unit("bpl_events")


def test_real_fixtures_parse_without_rejects():
    assert len(parse(BPL, "bpl_events/payload_0.xml").valid) == 5
    everywhere = unit("hclib_events", cities=[])
    parsed = parse(everywhere, "hclib_events/payload_0.xml")
    assert len(parsed.valid) == 5 and not parsed.rejects
    assert not parse(BPL, "bpl_events/payload_0.xml").rejects


def test_city_filter_keeps_only_configured_branch_cities():
    evs = by_id(parse(HCLIB, "hclib_events/payload_0.xml"))
    assert set(evs) == {"6a6d13b7f4e5db3d00c5ae37", "6a6d28a24523092f0034003b"}  # the two Minneapolis branches


def test_field_mapping_local_time_and_registration():
    evs = by_id(parse(unit("hclib_events", cities=[]), "hclib_events/payload_0.xml"))
    craft = evs["6a6d0d5ef4e5db3d00c5aba3"]
    assert craft.title == "Watch the Movie, Make the Craft"
    # bc:start_date_local is wall-clock in the city's zone (bc:start_date is the same instant in UTC)
    assert craft.start.isoformat() == "2026-10-17T09:30:00-05:00"
    assert craft.end is not None and craft.end.isoformat() == "2026-10-17T11:30:00-05:00"
    assert craft.location.venue_name == "Hennepin County Library – Maple Plain"
    assert craft.location.address == "5184 Main St. E., Maple Plain, MN, 55359"  # trailing comma in bc:city removed
    assert craft.location.lat == pytest.approx(45.0077, abs=1e-3)
    assert "registration_required" in craft.tags and craft.availability == "registration_open"
    assert craft.extras == {"capacity": 40, "registered": 1}
    assert craft.category == "arts.workshop"  # "Arts and Crafts" via category_map
    assert evs["6a6be0f574e3b8b75db64e39"].category == "family.kids"  # Baby Storytime
    assert "543-KNOW" not in dump(parse(unit("hclib_events", cities=[]), "hclib_events/payload_0.xml"))


def test_date_only_local_start_is_all_day():
    evs = by_id(parse(BPL, "bpl_events/payload_0.xml"))
    swap = evs["6ab6af430c7bf418f4e3f37d"]
    assert swap.all_day and swap.start.isoformat() == "2026-10-17T00:00:00-04:00"
    assert evs["6a207db24407827f8aa26702"].category == "trivia_games.board_games"  # Chess Club


def test_cancelled_virtual_and_broken_items():
    xml = b"""<?xml version="1.0"?><rss xmlns:bc="http://bibliocommons.com/rss/1.0/modules/event/"><channel>
    <item><title>Gone</title><guid>https://x/events/a1</guid><bc:start_date_local>2026-10-20T18:00</bc:start_date_local>
      <bc:is_cancelled>true</bc:is_cancelled></item>
    <item><title>Zoom talk</title><guid>https://x/events/a2</guid><bc:start_date_local>2026-10-20T18:00</bc:start_date_local>
      <bc:is_virtual>true</bc:is_virtual></item>
    <item><title>No date</title><guid>https://x/events/a3</guid></item>
    </channel></rss>"""
    parsed = parse_payloads(
        get_adapter("bibliocommons"), unit("hclib_events", cities=[]), [(Payload("u", 200, xml, NOW, "xml"), None)], NOW
    )
    evs = by_id(parsed)
    assert evs["a1"].availability == "cancelled"
    assert "a2" not in evs  # online-only events are skipped by default
    assert len(parsed.rejects) == 1 and "missing" in parsed.rejects[0][1]


def test_refuses_xml_with_entity_declarations():
    bomb = b'<?xml version="1.0"?><!DOCTYPE rss [<!ENTITY a "aaaa">]><rss><channel>&a;</channel></rss>'
    with pytest.raises(ValueError, match="DOCTYPE"):
        safe_xml(bomb)


def test_fetch_pages_until_a_short_page(tmp_path, settings):
    full = fixture_bytes("bpl_events/payload_0.xml")
    pages = []

    def handler(req):
        pages.append(dict(req.url.params))
        return httpx.Response(200, content=full)  # 5 items < 25 per page → last page

    t = FixtureTransport().add_fn(r"gateway\.bibliocommons\.com/v2/libraries/bpl/rss/events", handler)
    fr = get_adapter("bibliocommons").fetch(fetch_ctx(BPL, client(t, tmp_path), settings))
    assert len(fr.payloads) == 1 and fr.complete
    assert pages[0] == {"startDate": "2026-10-15", "endDate": "2026-10-25", "page": "1"}


def test_kcls_countywide_feed_keeps_only_branches_near_seattle():
    """King County Library System (real recorded page): Skykomish, Federal Way, Sammamish, Carnation are out."""
    kcls = unit("kcls_events")
    everywhere = parse(unit("kcls_events", cities=[]), "kcls_events/payload_0.xml")
    near = parse(kcls, "kcls_events/payload_0.xml")
    assert not everywhere.rejects and not near.rejects
    assert len(everywhere.valid) == 9
    cities = {str(ev.location.address).split(", ")[-3] for ev, _ in near.valid}
    assert cities and cities <= {"Tukwila", "Seatac", "Shoreline"}
    assert len(near.valid) == 5
    assert all(str(ev.location.venue_name).startswith("King County Library System – ") for ev, _ in near.valid)
