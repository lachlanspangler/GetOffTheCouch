"""Openings from liquor/business-license data via the generic Socrata adapter (real recorded rows)."""

import httpx

from gotc.adapters.base import get_adapter
from tests.adapters._util import by_id, client, dump, fetch_ctx, parse, unit
from tests.conftest import FixtureTransport

FIXTURED = [
    "nys_sla_pending_openings",
    "nys_sla_new_licenses",
    "seattle_business_openings",
    "chicago_liquor_openings",
    "tabc_pending_openings_austin",
    "la_business_openings",
    "colorado_liquor_openings_denver",
]


def test_real_fixtures_parse_without_rejects():
    for sid in FIXTURED:
        parsed = parse(unit(sid), f"{sid}/payload_0.json")
        assert parsed.valid and not parsed.rejects, (sid, parsed.rejects[:2])
        for ev, _ in parsed.valid:
            assert ev.kind == "opening" and ev.all_day, sid
            assert ev.category in ("food_drink.restaurant_opening", "nightlife.opening"), sid
            assert ev.description and ev.description.startswith("License signal, not a confirmed opening date"), sid
            assert ev.start.hour == 0 and ev.start.tzinfo is not None, sid


def test_ny_sla_pending_mapping_and_bar_detection():
    evs = by_id(parse(unit("nys_sla_pending_openings"), "nys_sla_pending_openings/payload_0.json"))
    rudy = evs["NA-0370-26-129802"]
    assert rudy.title == "Rudy's Bar & Grill — new liquor license application"
    assert rudy.category == "nightlife.opening"  # "Bar" in the name; the SLA class is just "Food & Beverage"
    assert rudy.start.isoformat() == "2026-10-15T00:00:00-04:00"  # received 13:35 local → that NYC calendar day
    assert rudy.location.address == "627 9th Ave, New York, 10036"
    assert (rudy.location.lat, rudy.location.lon) == (40.75992, -73.99155)
    assert "status: IntakeComplete" in (rudy.description or "")
    # no DBA: an LLC legal name is an organisation, so it may be shown
    assert evs["NA-0340-26-130796"].title.startswith("20X Hospitality at Long Island City LLC")


def test_shouty_names_are_title_cased_and_lounges_are_nightlife():
    evs = by_id(parse(unit("nys_sla_new_licenses"), "nys_sla_new_licenses/payload_0.json"))
    assert evs["0370-24-132795"].title == "Bar Bayeux — new liquor license"
    assert evs["0370-24-134293"].category == "nightlife.opening"  # WXYZ LOUNGE
    assert evs["0370-24-132070"].category == "food_drink.restaurant_opening"  # Epicerie Boulud


def test_seattle_compact_dates_future_openings_and_no_phone_numbers():
    parsed = parse(unit("seattle_business_openings"), "seattle_business_openings/payload_0.json")
    titles = {ev.title: ev for ev, _ in parsed.valid}
    virtue = titles["Virtue Coffee And Cocktails — new business license"]
    assert virtue.start.isoformat() == "2026-12-01T00:00:00-08:00"  # "20261201", a pre-registered opening
    assert virtue.category == "nightlife.opening"  # NAICS "Drinking Places (Alcoholic Beverages)"
    text = dump(parsed)
    for phone in ("9712884288", "2062279591", "2069102118", "4255053069"):
        assert phone not in text


def test_tabc_owner_names_never_emitted_and_red_sign_means_bar():
    parsed = parse(unit("tabc_pending_openings_austin"), "tabc_pending_openings_austin/payload_0.json")
    text = dump(parsed)
    for owner in ("Sakura-Texas LLC", "Lola's CC LLC", "RTB ATX", "JewBoy Hyde Park", "You Already Know"):
        assert owner not in text
    evs = {ev.title: ev for ev, _ in parsed.valid}
    assert evs["Palace Laundry — new liquor license application"].category == "nightlife.opening"  # gun_sign RED
    assert evs["Panciuto — new liquor license application"].category == "food_drink.restaurant_opening"


def test_person_like_legal_names_are_withheld_not_shown():
    u = unit("nys_sla_pending_openings")
    rows = [
        {"application_id": "A1", "legalname": "Jane Q Smith", "received_date": "2026-10-01T10:00:00.000"},
        {"application_id": "A2", "legalname": "Smith Hospitality LLC", "received_date": "2026-10-01T10:00:00.000"},
    ]
    import json

    from gotc.adapters.base import Payload
    from gotc.pipeline.ingest import parse_payloads
    from tests.conftest import NOW

    parsed = parse_payloads(get_adapter("socrata"), u, [(Payload("u", 200, json.dumps(rows).encode(), NOW), None)], NOW)
    assert [ev.record_id for ev, _ in parsed.valid] == ["A2"]
    assert len(parsed.rejects) == 1 and "withheld" in parsed.rejects[0][1]
    assert "Jane" not in parsed.rejects[0][0]  # the reject hint never stores the withheld name either


def test_colorado_swapped_column_rows_are_rejected():
    u = unit("colorado_liquor_openings_denver", exclude_regex={}, exclude_title=[])
    parsed = parse(u, "colorado_liquor_openings_denver/anomalies.json")
    assert not parsed.valid and len(parsed.rejects) == 5
    assert all("data-quality" in err or "future" in err for _, err, _ in parsed.rejects)
    ok = by_id(parse(unit("colorado_liquor_openings_denver"), "colorado_liquor_openings_denver/payload_0.json"))
    assert set(ok) == {"03-26557", "03-26896", "03-26746"}  # takeout permit + tobacco license excluded by config
    assert ok["03-26746"].category == "nightlife.opening"  # Brew Pub
    assert ok["03-26557"].start.isoformat() == "2026-09-30T00:00:00-06:00"


def test_la_zero_coordinates_are_dropped():
    evs = by_id(parse(unit("la_business_openings"), "la_business_openings/payload_0.json"))
    assert evs["0002976970-0005-7"].location.lat is None  # location_1 = (0.0, 0.0)
    assert evs["0003609124-0001-4"].title == "Sammie's — new business registration"


def test_where_template_uses_local_lookback_window(tmp_path, settings):
    seen = []

    def handler(req):
        seen.append(req.url.params["$where"])
        return httpx.Response(200, json=[])

    t = FixtureTransport().add_fn(r"cos-data\.seattle\.gov/resource/wnbq-64tb\.json", handler)
    get_adapter("socrata").fetch(fetch_ctx(unit("seattle_business_openings"), client(t, tmp_path), settings))
    # 2026-10-16T03:00Z is Oct 15 in Seattle → 60 days back = Aug 16; horizon 240 days ahead, compact YYYYMMDD
    assert "license_start_date >= '20260816'" in seen[0]
    assert "license_start_date < '20270612'" in seen[0]
