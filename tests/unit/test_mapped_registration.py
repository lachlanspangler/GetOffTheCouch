from datetime import UTC, datetime

from gotc.adapters.base import ParseContext
from gotc.adapters.mapped import map_rows
from tests.conftest import make_city, make_source, unit_for

NOW = datetime(2026, 10, 16, 15, tzinfo=UTC)
ROW = {
    "activity_id": "586506",
    "title": "Volleyball League at Mt. Greenwood",
    "start_date": "2026-10-22T18:30:00.000",
    "fee": "200",
    "registration_date": "2026-08-03T14:00:00.000",
    "date_notes": "Each Thursday from 6:30pm to 9:30pm",
    "information_link": {"url": "http://apm.activecommunities.com/chicagoparkdistrict/Activity_Search/586506"},
    "category": "Sports - Volleyball",
}


def ctx(**params):
    base = {
        "fields": {
            "record_id": "activity_id",
            "title": "title",
            "start": "start_date",
            "price": "fee",
            "recurrence": "date_notes",
            "registration_opens": "registration_date",
            "registration_url": "information_link",
            "category": "category",
        },
        "category_map": {"Sports - Volleyball": "sports_league.volleyball"},
        "kind": "season",
        **params,
    }
    src = make_source("cpd", "socrata", domain="x", dataset="y", **base)
    return ParseContext(unit=unit_for(src, make_city("chicago")), fetched_at=NOW)


def test_fee_recurrence_and_reported_opening():
    (rec,) = list(map_rows([dict(ROW)], ctx()))
    assert rec["price"]["min"] == 200 and rec["recurrence"].startswith("Each Thursday")
    reg = rec["registration"]
    assert reg["opens_at"].isoformat().startswith("2026-08-03T14:00")
    assert reg["closes_at"] is None and reg["method"] == "reported"
    assert rec["availability"] == "registration_open"


def test_closes_at_start_is_opt_in_and_labeled_derived():
    (rec,) = list(map_rows([dict(ROW)], ctx(registration_closes_at_start=True, signup_types=["team"])))
    reg = rec["registration"]
    assert reg["closes_at"] == rec["start"]
    assert reg["method"] == "derived" and reg["confidence"] == 0.5 and "No close date is published" in reg["evidence"]
    assert reg["signup_types"] == ["team"]


def test_zero_fee_is_free():
    (rec,) = list(map_rows([{**ROW, "fee": "0"}], ctx()))
    assert rec["price"] == {"is_free": True}
