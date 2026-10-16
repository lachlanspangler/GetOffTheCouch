"""Sacramento openings: City of Sacramento business-tax certificates (ArcGIS table, trade-name titles, no geometry)."""

from tests.adapters._util import by_id, dump, parse, unit

U = unit("sacramento_business_openings")


def test_parses_every_row_as_an_opening():
    parsed = parse(U, "sacramento_business_openings/payload_0.json")
    assert len(parsed.valid) == 6 and not parsed.rejects
    ev = by_id(parsed)["1124485"]
    assert ev.kind == "opening"
    assert ev.title == "Levels — new business registration"
    assert ev.category == "food_drink.restaurant_opening"
    assert ev.all_day and ev.start.isoformat().startswith("2026-")
    assert ev.location.address == "722, K, ST, SACRAMENTO, CA"
    assert (ev.description or "").startswith("License signal, not a confirmed opening date.")


def test_owner_contact_columns_are_never_requested():
    out_fields = U.source.params["out_fields"]
    assert "Owner" not in out_fields and "Phone" not in out_fields and "Mail_" not in out_fields
    assert "Principal_Owner" not in dump(parse(U, "sacramento_business_openings/payload_0.json"))
