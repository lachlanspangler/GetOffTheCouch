"""The shared config-driven row mapper (gotc/adapters/mapped.py): privacy, dates, coordinates, filters."""

from datetime import UTC, datetime

import pytest

from gotc.adapters.base import ParseContext
from gotc.adapters.common import title_case_if_shouty
from gotc.adapters.mapped import (
    PII_KEY,
    local_date,
    looks_like_entity,
    map_rows,
    sane_coords,
    scrub_phones,
    scrub_row,
    window_fmt,
)
from tests.conftest import NOW, make_city, make_source, unit_for


@pytest.mark.parametrize(
    "key",
    [
        "owner",
        "Business_Owner",
        "business_phone",
        "dayphn_cleaned",
        "day_phone",
        "manager",
        "applicant",
        "contact",
        "event_contact",
        "email",
        "mail_address",
        "mailing_city",
        "requestor_",
        "ssn",
    ],
)
def test_personal_columns_are_dropped(key):
    assert PII_KEY.search(key)
    assert key not in scrub_row({key: "x", "dba": "y"})


@pytest.mark.parametrize("key", ["businessname", "business_name", "dba_name", "trade_name", "address", "license_type"])
def test_business_columns_are_kept(key):
    assert not PII_KEY.search(key)  # regression: "businessname" contains "ssn"


def test_entity_heuristic():
    assert looks_like_entity("Rising Chol LLC") and looks_like_entity("ROTI CORNER INC")
    assert looks_like_entity("Knebel Post #83, The American Legion Club")
    assert not looks_like_entity("Jane Q Smith") and not looks_like_entity("DC Hudson 1")


def test_local_date_handles_utc_midnight_epochs_and_local_wall_clock():
    assert local_date(1791936000000, "America/Denver").isoformat() == "2026-10-14"  # 00:00Z date-only value
    assert local_date(1790917200000, "America/Chicago").isoformat() == "2026-10-02"  # 05:00Z = local midnight
    assert local_date("2026-09-09 16:40:00.293+00", "America/New_York").isoformat() == "2026-09-09"
    assert local_date("2026-10-16 02:30:00+00", "America/New_York").isoformat() == "2026-10-15"  # evening ET
    assert local_date("20261218", "America/Los_Angeles").isoformat() == "2026-12-18"
    assert local_date("", "America/Chicago") is None and local_date("garbage", "America/Chicago") is None


def test_phone_scrub_and_title_case():
    assert scrub_phones("call (617) 254-7564 or 612.543.5669") == "call [phone removed] or [phone removed]"
    assert title_case_if_shouty("LUCKY'S PUB") == "Lucky's Pub"
    assert title_case_if_shouty("Rudy's Bar") == "Rudy's Bar"


def test_coordinates_outside_the_city_are_dropped():
    src = make_source("s", "socrata", fields={"title": "t", "start": "s"})
    ctx = ParseContext(unit_for(src, make_city("minneapolis", [src])), NOW)
    assert sane_coords(44.98, -93.27, ctx) == (44.98, -93.27)
    assert sane_coords(0.0, 0.0, ctx) == (None, None)
    assert sane_coords(34.91, -115.50, ctx) == (None, None)
    assert sane_coords(None, -93.2, ctx) == (None, None)


def test_window_placeholders_are_local_and_honor_lookback():
    fmt = window_fmt(
        datetime(2026, 10, 16, 3, 0, tzinfo=UTC), "America/Chicago", {"lookback_days": 60, "horizon_days": 10}
    )
    assert fmt["today_date"] == "2026-08-16" and fmt["today_compact"] == "20260816"
    assert fmt["asof_date"] == "2026-10-15" and fmt["horizon_date"] == "2026-10-25"
    assert fmt["today"] == "2026-08-16T00:00:00"


def test_filters_templates_and_rejects():
    src = make_source(
        "s",
        "socrata",
        fields={"record_id": "id", "title": ["dba", "legal"], "start": "d", "category": "kind", "description": "notes"},
        entity_only_fields=["legal"],
        kind="opening",
        include_regex={"kind": "(?i)tavern|restaurant"},
        exclude_title=["(?i)grocery"],
        title_template="{title} — new license",
        description_template="License signal, not a confirmed opening date ({kind}, {date}).",
        validate={"id": r"^\d+$"},
        reject_future_start=True,
    )
    ctx = ParseContext(unit_for(src, make_city("minneapolis", [src])), NOW)
    rows = [
        {
            "id": "1",
            "dba": "THE DIVE",
            "d": "2026-10-01",
            "kind": "Tavern",
            "notes": "Owner cell 612-555-0100",
            "owner": "Pat Doe",
        },
        {"id": "2", "dba": "Corner Grocery", "d": "2026-10-01", "kind": "Restaurant"},
        {"id": "3", "dba": "Car Wash", "d": "2026-10-01", "kind": "Car Wash"},
        {"id": "x9", "dba": "Bad Id Bar", "d": "2026-10-01", "kind": "Tavern"},
        {"id": "5", "dba": "Time Traveler Tavern", "d": "2226-10-01", "kind": "Tavern"},
        {"id": "6", "legal": "Pat Doe", "d": "2026-10-01", "kind": "Restaurant"},
    ]
    out = list(map_rows(rows, ctx))
    good = [r for r in out if "_reject" not in r]
    assert [r["record_id"] for r in good] == ["1"]
    dive = good[0]
    assert dive["title"] == "The Dive — new license" and dive["category"] == "nightlife.opening"
    assert dive["description"].startswith("License signal, not a confirmed opening date (Tavern, Oct 1, 2026).")
    assert "612-555-0100" not in dive["description"] and "Pat Doe" not in str(out)
    assert dive["start"].isoformat() == "2026-10-01T00:00:00-05:00" and dive["all_day"]
    reasons = sorted(r["_reject"] for r in out if "_reject" in r)
    assert len(reasons) == 3
    assert any("data-quality" in r for r in reasons) and any("future" in r for r in reasons)
    assert any("withheld" in r for r in reasons)
