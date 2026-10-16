"""Communico calendar adapter against a real recorded Miami-Dade Public Library day."""

import json

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import by_id, client, dump, fetch_ctx, parse, unit
from tests.conftest import NOW, FixtureTransport

MDPLS = unit("mdpls_events")
FX = "mdpls_events/payload_0.json"


def test_real_fixture_parses_without_rejects():
    parsed = parse(MDPLS, FX)
    assert len(parsed.valid) == 3 and not parsed.rejects  # 5 "All day" exhibits/displays are skipped by config
    keep_all = parse(unit("mdpls_events", skip_all_day=False), FX)
    assert len(keep_all.valid) == 8 and not keep_all.rejects


def test_field_mapping_local_time_and_registration():
    evs = by_id(parse(MDPLS, FX))
    ss = evs["17243791"]
    assert ss.title == "Social Security 101"
    assert ss.start.isoformat() == "2026-10-16T09:30:00-04:00"  # raw_start_time is Miami wall-clock
    assert ss.end is not None and ss.end.isoformat() == "2026-10-16T11:00:00-04:00"
    assert ss.availability == "registration_open" and "registration_required" in ss.tags
    assert ss.extras["capacity"] == 10
    assert ss.location.venue_name is not None and ss.location.venue_name.startswith("Miami-Dade Public Library – ")
    assert evs["17171826"].category == "arts.workshop"  # "Arts & Crafts" via category_map


def test_staff_contact_names_are_never_emitted():
    text = dump(parse(unit("mdpls_events", skip_all_day=False), FX))
    for name in ("Jennifer Shipley", "Martin Kass", "Katherine Moore", "Oscar Fuentes"):
        assert name not in text


def test_virtual_full_and_broken_rows():
    base = {"raw_start_time": "2026-10-20 18:00:00", "raw_end_time": "2026-10-20 19:00:00", "time_string": "6pm"}
    body = [
        {**base, "id": "1", "title": "Zoom Book Talk", "event_type": "VIRTUAL"},
        {
            **base,
            "id": "2",
            "title": "Teen Coding Club",
            "event_type": "INPERSON",
            "allow_reg": "1",
            "max_attendee": "12",
            "total_registrants": "12",
            "allow_waitlist": "1",
            "reg_url": "https://mdpls.org/r/2",
        },
        {"id": "3", "title": "", "raw_start_time": ""},
    ]
    parsed = parse_payloads(
        get_adapter("communico"), MDPLS, [(Payload("u", 200, json.dumps(body).encode(), NOW), None)], NOW
    )
    evs = by_id(parsed)
    assert "1" not in evs
    assert evs["2"].availability == "waitlist" and evs["2"].offers[0].kind == "registration"
    assert len(parsed.rejects) == 1


def test_fetch_requests_one_local_day_at_a_time(tmp_path, settings):
    t = FixtureTransport().add(r"mdpls\.org/eeventcaldata", [])
    fr = get_adapter("communico").fetch(fetch_ctx(MDPLS, client(t, tmp_path), settings))
    assert len(fr.payloads) == 7
    first = next(c for c in t.calls if "eeventcaldata" in c)
    assert "2026-10-15" in first.replace("%22", '"')  # 2026-10-16T03:00Z is still Oct 15 in Miami
