"""ArcGIS FeatureServer adapter against real recorded layers (Nashville beer permits, Denver liquor/pending food)."""

import json

import pytest

from gotc.adapters.base import get_adapter
from tests.adapters._util import by_id, client, dump, fetch_ctx, parse, unit
from tests.conftest import FixtureTransport

NASH = unit("nashville_beer_permit_openings")
DEN_LIQ = unit("denver_liquor_openings")
DEN_FOOD = unit("denver_pending_food_openings")


def test_real_fixture_parses_without_rejects():
    for u in (NASH, DEN_LIQ, DEN_FOOD):
        parsed = parse(u, f"{u.source.id}/payload_0.json")
        assert parsed.valid and not parsed.rejects, u.source.id


def test_nashville_openings_field_mapping_and_local_dates():
    parsed = parse(NASH, "nashville_beer_permit_openings/payload_0.json")
    evs = by_id(parsed)
    # only on-premises permits; "BB - Special Events" temporaries are filtered by config
    assert set(evs) == {"T26-30199", "T26-30189"}
    pub = evs["T26-30199"]
    assert pub.title == "Lucky's Pub — new beer permit"  # shouty name title-cased, possessive intact
    assert pub.kind == "opening" and pub.all_day
    assert pub.category == "nightlife.opening"
    assert evs["T26-30189"].category == "food_drink.restaurant_opening"
    # Date_Entered 1790917200000 = 2026-10-02T05:00Z = local midnight in Nashville
    assert pub.start.isoformat() == "2026-10-02T00:00:00-05:00"
    assert pub.location.address == "579 STEWARTS FERRY PIKE, NASHVILLE, 37214"
    assert pub.location.lat == pytest.approx(36.1585593)
    assert "not a confirmed opening date" in (pub.description or "")


def test_openings_never_emit_owner_names():
    parsed = parse(NASH, "nashville_beer_permit_openings/payload_0.json")
    assert "Jeanne Heaton" not in dump(parsed)
    # even if config tried to show the special-event permit that carries an owner name
    loose = unit("nashville_beer_permit_openings", include_regex={}, description_template="{Business_Owner}")
    parsed = parse(loose, "nashville_beer_permit_openings/payload_0.json")
    assert len(parsed.valid) == 5 and "Jeanne Heaton" not in dump(parsed)


def test_denver_utc_midnight_dates_keep_their_calendar_day():
    evs = by_id(parse(DEN_FOOD, "denver_pending_food_openings/payload_0.json"))
    # APPLICATION_DATE 1791936000000 = 2026-10-14T00:00Z: a date-only value, NOT Oct 13 6pm in Denver
    assert "2026-BFN-0023229" not in evs  # "Baba & Co Catering": caterers are excluded
    beer_hall = evs["2026-BFN-0022682"]
    assert beer_hall.title == "The Larimer Beer Hall — new restaurant license application"
    assert beer_hall.category == "nightlife.opening"
    assert evs["2026-BFN-0023060"].start.isoformat() == "2026-10-13T00:00:00-06:00"
    assert beer_hall.location.lat is None  # this layer has null geometry → geocoded later from the address


def test_placeholder_geometry_far_outside_the_city_is_dropped():
    evs = by_id(parse(DEN_LIQ, "denver_liquor_openings/payload_0.json"))
    assert evs["2026-BFN-0021063"].location.lat is None  # (-115.5, 34.9) is the California desert
    argonaut = evs["2026-BFN-0022697"]
    assert argonaut.location.lat == pytest.approx(39.7398, abs=1e-3)
    assert argonaut.location.neighborhood == "Capitol Hill"
    assert argonaut.start.isoformat() == "2026-10-14T00:00:00-06:00"


def test_fetch_pages_until_exceeded_transfer_limit_clears(tmp_path, settings):
    t = FixtureTransport()
    pages = [
        {
            "type": "FeatureCollection",
            "features": [{"properties": {"Permit__": "A"}}],
            "properties": {"exceededTransferLimit": True},
        },
        {"type": "FeatureCollection", "features": [{"properties": {"Permit__": "B"}}]},
    ]
    seen = []

    def handler(req):
        import httpx

        offset = int(req.url.params["resultOffset"])
        seen.append(dict(req.url.params))
        return httpx.Response(200, json=pages[0 if offset == 0 else 1])

    t.add_fn(r"/FeatureServer/0/query", handler)
    u = unit("nashville_beer_permit_openings", page_size=1)
    fr = get_adapter("arcgis").fetch(fetch_ctx(u, client(t, tmp_path), settings))
    assert len(fr.payloads) == 2 and fr.complete
    assert seen[0]["outSR"] == "4326" and seen[0]["f"] == "geojson"
    assert seen[0]["where"].startswith("Date_Entered >= DATE '2026-08-16'")  # 60-day lookback, local date
    assert seen[1]["resultOffset"] == "1"


def test_fetch_raises_on_arcgis_error_body(tmp_path, settings):
    t = FixtureTransport().add(r"/query", {"error": {"code": 400, "message": "Invalid query", "details": []}})
    with pytest.raises(ValueError, match="ArcGIS error 400"):
        get_adapter("arcgis").fetch(fetch_ctx(NASH, client(t, tmp_path), settings))


def test_esri_json_geometry_and_broken_rows_are_handled():
    from gotc.adapters.base import ParseContext, Payload
    from tests.conftest import NOW

    body = {
        "features": [
            {
                "attributes": {
                    "Permit__": "X1",
                    "Business_Name": "Ember Bar",
                    "Date_Entered": 1790917200000,
                    "Permit_Subtype_Description": "BB - On Site Sales",
                },
                "geometry": {"x": -86.78, "y": 36.16},
            },
            {
                "attributes": {
                    "Permit__": "X2",
                    "Business_Name": "",
                    "Date_Entered": None,
                    "Permit_Subtype_Description": "BB - On Site Sales",
                }
            },
        ]
    }
    recs = list(get_adapter("arcgis").parse(Payload("u", 200, json.dumps(body).encode(), NOW), ParseContext(NASH, NOW)))
    assert recs[0]["location"]["lat"] == 36.16
    assert "_reject" in recs[1]
