"""Philadelphia (batch A): L&I business licenses from the city's Carto SQL API, as CSV, through ``csvfile``.

New platform variant: ``phl.carto.com/api/v2/sql?format=csv&q=…`` (OpenDataPhilly). The query itself selects only
non-personal columns and first-issued food-service licenses; the config's ``exclude_title`` drops child-care
centers and schools that also hold food licenses. Real recorded response, trimmed to 8 rows.
"""

from gotc.adapters.base import Payload, get_adapter
from gotc.pipeline.ingest import parse_payloads
from tests.adapters._util import unit
from tests.conftest import NOW, fixture_bytes

PHL = unit("phl_restaurant_openings")


def _parse():
    p = Payload(str(PHL.source.params["url"]), 200, fixture_bytes("phl_restaurant_openings/payload_0.csv"), NOW, "csv")
    return parse_payloads(get_adapter("csvfile"), PHL, [(p, None)], NOW)


def test_carto_csv_openings():
    parsed = _parse()
    assert not parsed.rejects
    evs = {ev.record_id: ev for ev, _ in parsed.valid}
    assert "1021005" in evs  # licensenum is the record id
    wings = evs["1021005"]
    assert wings.title == "Fallin off the Bone Wings West LLC — new food-service license"
    assert wings.kind == "opening" and wings.category == "food_drink.restaurant_opening"
    assert wings.start.date().isoformat() == "2026-10-15"
    assert wings.location.lat is not None and abs(wings.location.lat - 39.994) < 0.01
    assert wings.description.startswith("License signal, not a confirmed opening date.")


def test_child_care_and_preschool_food_licenses_are_not_openings():
    titles = " ".join(ev.title for ev, _ in _parse().valid)
    assert "CHILD CARE" not in titles.upper()
    assert "CREATIVE BEGINNINGS" not in titles.upper()
