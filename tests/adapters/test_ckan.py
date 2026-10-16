"""CKAN DataStore adapter against real recorded data.boston.gov responses."""

import httpx
import pytest

from gotc.adapters.base import get_adapter
from tests.adapters._util import by_id, client, dump, fetch_ctx, parse, unit
from tests.conftest import FixtureTransport

FOOD = unit("boston_food_openings")
SPECIAL = unit("boston_special_events")


def test_real_fixtures_parse_without_rejects():
    for u in (FOOD, SPECIAL):
        parsed = parse(u, f"{u.source.id}/payload_0.json")
        assert len(parsed.valid) == 5 and not parsed.rejects, u.source.id


def test_food_openings_mapping_timezone_and_privacy():
    parsed = parse(FOOD, "boston_food_openings/payload_0.json")
    evs = by_id(parsed)
    bloom = evs["352651"]
    assert bloom.title == "Bloom — new food license"
    assert bloom.kind == "opening" and bloom.all_day
    # license_add_dt_tm "2026-09-09 16:40:00.293+00" → the Boston calendar day, as local midnight
    assert bloom.start.isoformat() == "2026-09-09T00:00:00-04:00"
    assert bloom.location.address == "23 Northern, Boston, 02210"
    assert bloom.location.lat == pytest.approx(42.3534, abs=1e-3)
    assert evs["15025"].category == "nightlife.opening"  # "Spy Bar"
    assert bloom.category == "food_drink.restaurant_opening"
    text = dump(parsed)
    for phone in ("7186667214", "6179827798", "_full_text"):
        assert phone not in text  # dayphn_cleaned and CKAN's full-text index are never mapped


def test_special_events_all_day_with_end_date():
    evs = by_id(parse(SPECIAL, "boston_special_events/payload_0.json"))
    rodeo = evs["PUB1872170:2026-10-16"]
    assert rodeo.title == "Boston Rodeo"
    assert rodeo.all_day and rodeo.start.isoformat() == "2026-10-16T00:00:00-04:00"
    assert rodeo.end is not None and rodeo.end.isoformat() == "2026-10-17T23:59:00-04:00"
    assert rodeo.location.address == "306, Northern, AV, Boston, 02210"
    one_day = evs["PUB1904154:2026-10-16"]
    assert one_day.end is None


def test_fetch_builds_sql_and_pages(tmp_path, settings):
    sqls = []

    def handler(req):
        sqls.append(req.url.params["sql"])
        n = 2 if len(sqls) == 1 else 1
        return httpx.Response(200, json={"success": True, "result": {"records": [{"_id": i} for i in range(n)]}})

    t = FixtureTransport().add_fn(r"datastore_search_sql", handler)
    u = unit("boston_food_openings", page_size=2)
    fr = get_adapter("ckan").fetch(fetch_ctx(u, client(t, tmp_path), settings))
    assert len(fr.payloads) == 2
    assert sqls[0] == (
        "SELECT * FROM \"f1e13724-284d-478c-b8bc-ef042aa5b70b\" WHERE descript = 'Eating & Drinking' AND "
        "license_add_dt_tm >= '2026-08-16' ORDER BY license_add_dt_tm DESC LIMIT 2 OFFSET 0"
    )
    assert sqls[1].endswith("LIMIT 2 OFFSET 2")


def test_fetch_resolves_resource_from_package_and_raises_on_failure(tmp_path, settings):
    t = FixtureTransport()
    t.add(
        r"package_show",
        {
            "success": True,
            "result": {
                "resources": [
                    {"id": "old", "name": "Archive", "datastore_active": False},
                    {"id": "cur-123", "name": "Active Food Establishment Licenses", "datastore_active": True},
                ]
            },
        },
    )
    t.add(r"datastore_search_sql", {"success": False, "error": {"message": "relation does not exist"}})
    u = unit("boston_food_openings", resource_id=None, package="food-licenses")
    with pytest.raises(ValueError, match="relation does not exist"):
        get_adapter("ckan").fetch(fetch_ctx(u, client(t, tmp_path), settings))
    assert any('"cur-123"' in httpx.URL(c).params.get("sql", "") for c in t.calls)
