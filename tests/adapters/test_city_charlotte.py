"""Charlotte units on new platform variants: the CMPD events table on the city's self-hosted ArcGIS Server
(MapServer table, ``format: json``, no geometry, robots honoured)."""

from tests.adapters._util import by_id, dump, parse, unit

CMPD = unit("clt_cmpd_community_events")


def test_cmpd_table_parses_without_rejects():
    parsed = parse(CMPD, "clt_cmpd_community_events/payload_0.json")
    assert len(parsed.valid) == 5 and not parsed.rejects


def test_cmpd_mapping_local_times_and_title():
    evs = by_id(parse(CMPD, "clt_cmpd_community_events/payload_0.json"))
    ev = evs["1154:2026-10-19"]
    # shouty description title-cased, division appended by title_template
    assert ev.title == "Shannon Park Community Meeting (CMPD North Tryon Division)"
    assert ev.category == "community.neighborhood"
    # EVENTSTARTDATETIME 1792447200000 = 2026-10-19T22:00Z = 6 pm in Charlotte
    assert ev.start.isoformat() == "2026-10-19T18:00:00-04:00"
    assert ev.end is not None and ev.end.isoformat() == "2026-10-19T19:00:00-04:00"
    assert ev.location.venue_name == "GREATER BETHEL AME CHURCH"
    assert ev.location.lat is None  # table has no geometry → geocoded later from the street address
    assert ev.price.is_free


def test_cmpd_contact_phones_never_emitted():
    parsed = parse(CMPD, "clt_cmpd_community_events/payload_0.json")
    out = dump(parsed)
    assert "7044322461" not in out and "336-8300" not in out
