"""csvfile adapter: Florida DBPR retail beverage license extract (real lines of bd4006lic.csv, 2026-10-16)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from gotc.adapters.base import get_adapter
from gotc.adapters.csvfile import decode, snake
from gotc.config import Unit
from gotc.settings import Settings
from tests.adapters._util import by_id, client, dump, fetch_ctx, parse, unit
from tests.conftest import FIXTURES, FixtureTransport, make_city, make_source

FIX = "fl_dbpr_openings_miami/payload_0.csv"
ET = ZoneInfo("America/New_York")


def test_real_extract_maps_recent_on_premises_licenses_with_no_rejects() -> None:
    parsed = parse(unit("fl_dbpr_openings_miami"), FIX)
    assert parsed.rejects == []
    evs = by_id(parsed)
    # in the 60-day window, county 23, series *COP, not an inactive quota license in escrow
    assert set(evs) == {
        "BEV2339129",  # SOFIBEAN CAFE INC (08/20/2026)
        "BEV2339137",  # AMI AMI (08/27)
        "BEV2335123",  # FLIGHT WINE LOUNGE (08/24)
        "BEV2339158",  # 27 CLUB (09/08)
        "BEV2338158",  # TOSTAO CAFE RESTAURANT (09/23)
        "BEV2339193",  # LA PECORA BIANCA (10/14)
        "BEV2339196",  # MIDORIE MIAMI (10/14)
    }
    ami = next(ev for ev in evs.values() if ev.title.startswith("Ami Ami"))
    assert ami.title == "Ami Ami — new liquor license"
    assert ami.kind.value == "opening" and ami.all_day
    assert ami.start == datetime(2026, 8, 27, 0, 0, tzinfo=ET)  # Original Licensure Date, local midnight
    assert ami.location.address == "318 MIRACLE MILE, CORAL GABLES, FL"
    assert ami.description and ami.description.startswith("License signal, not a confirmed opening date.")
    assert "series 2COP" in ami.description and "Aug 27, 2026" in ami.description
    assert ami.source_categories == ["2COP"]
    cats = {ev.title: ev.category for ev in evs.values()}
    assert cats["27 CLUB — new liquor license"] == "nightlife.opening"
    assert cats["Flight Wine Lounge — new liquor license"] == "nightlife.opening"
    assert cats["La Pecora Bianca — new liquor license"] == "food_drink.restaurant_opening"


def test_filters_are_filters_not_rejects() -> None:
    titles = " ".join(ev.title for ev, _ in parse(unit("fl_dbpr_openings_miami"), FIX).valid)
    assert "Haisley" not in titles  # Gainesville (county 11)
    assert "Big Cheese" not in titles  # no Original Licensure Date (2002 effective date only)
    assert "Crown Tobacco" not in titles  # 2APS = package sales, not on-premises
    assert "Wynwood Factory" not in titles and "Escrow" not in titles  # inactive quota licenses
    assert "Jet Runway" not in titles  # licensed 02/04/2026: outside the 60-day window


def test_privacy_owner_and_mailing_columns_never_reach_a_record() -> None:
    parsed = parse(unit("fl_dbpr_openings_miami"), FIX)
    blob = dump(parsed).lower()
    for owner in ("cultura nest llc", "kcs hospitality group llc", "lpb9 llc", "eli and yoan corp"):
        assert owner not in blob  # "Owner Name" (owner_name) is dropped by the PII scrub
    for mail in ("12401  sw 68th ct", "17410 nw 48 avenue", "miami gardens"):
        assert mail not in blob  # "Mail Address 1" → mail_address_1, also scrubbed
    assert "terminello" not in blob


def test_a_dba_that_repeats_a_persons_name_is_withheld() -> None:
    # widen the window and drop the inactive filter so the trustee's row reaches the mapping
    u = unit("fl_dbpr_openings_miami", lookback_days=400, exclude_regex={})
    parsed = parse(u, FIX)
    withheld = [(h, e) for h, e, _ in parsed.rejects if "withheld" in e]
    assert len(withheld) == 1  # LOUIS J TERMINELLO AS TRUSTEE (DBA == owner, not an organisation)
    assert all("terminello" not in h.lower() for h, _ in withheld)  # not even in the reject hint
    assert "terminello" not in dump(parsed).lower()
    # an organisation-looking DBA that repeats the legal name is still used ("SOFIBEAN CAFE INC")
    assert any(ev.title.startswith("Sofibean Cafe Inc") for ev, _ in parsed.valid)
    # the non-ASCII DBA decodes as UTF-8
    assert any(ev.title == "Jet Runway Café Express — new liquor license" for ev, _ in parsed.valid)


def test_encoding_fallback_and_header_normalisation() -> None:
    raw = (FIXTURES / FIX).read_bytes()
    assert decode(raw, ["utf-8-sig", "cp1252"])[1] == "utf-8-sig"
    latin = raw.decode("utf-8").encode("cp1252")  # same file as a Windows-1252 export
    text, used = decode(latin, ["utf-8-sig", "cp1252"])
    assert used == "cp1252" and "JET RUNWAY CAFÉ EXPRESS" in text
    assert snake("Mail Address 1") == "mail_address_1" and snake("﻿Owner Name") == "owner_name"


def test_headerless_daily_transactions_file_with_positional_columns() -> None:
    """The research sample of DBPR's headerless daily.csv (docs/research/samples, real rows)."""
    cols = [
        "profession", "county", "license_number", "series", "modifier", "dba", "licensee", "address1",
        "address2", "address3", "city", "state", "zip", "transaction_date", "transaction_code",
        "transaction", "flag",
    ]  # fmt: skip
    src = make_source(
        "fl_daily",
        adapter="csvfile",
        url="https://example.test/daily.csv",
        columns=cols,
        kind="opening",
        lookback_days=10,
        window={"field": "transaction_date"},
        include={"county": ["Dade"]},
        fields={"record_id": "license_number", "title": ["dba", "licensee"], "start": "transaction_date",
                "address": ["address1", "city"]},
        entity_only_fields=["licensee"],
    )  # fmt: skip
    city = make_city("miami").model_copy(update={"timezone": "America/New_York", "center": (25.7617, -80.1918)})
    sample = Path(__file__).parents[2] / "docs/research/samples/fl_dbpr_abt_daily_transactions_dade.csv"
    from gotc.adapters.base import Payload
    from gotc.pipeline.ingest import parse_payloads
    from tests.conftest import NOW

    p = Payload("https://example.test/daily.csv", 200, sample.read_bytes(), NOW, "csv")
    parsed = parse_payloads(get_adapter("csvfile"), Unit(source=src, city=city), [(p, None)], NOW)
    assert parsed.rejects == []
    titles = sorted(ev.title for ev, _ in parsed.valid)
    assert "La Taberna De Ignacio" in titles and "Membership Drive" in titles
    assert all(ev.start.date().isoformat() == "2026-10-14" for ev, _ in parsed.valid)


def test_fetch_rejects_html_and_honours_robots(tmp_path: Path, settings: Settings) -> None:
    t = FixtureTransport()
    t.add("myfloridalicense.com/robots.txt", "User-agent: *\nDisallow: /wp-admin/\n")
    t.add(r"extracts/bd4006lic\.csv", (FIXTURES / FIX).read_bytes())
    u = unit("fl_dbpr_openings_miami")
    fr = get_adapter("csvfile").fetch(fetch_ctx(u, client(t, tmp_path), settings))
    assert fr.payloads[0].content_type == "csv" and fr.complete
    assert any(c.endswith("/robots.txt") for c in t.calls)


BOS = "boston_food_openings_csv/payload_0.csv"


def test_boston_food_licenses_from_the_csv_download() -> None:
    parsed = parse(unit("boston_food_openings_csv"), BOS)
    assert parsed.rejects == []
    titles = sorted(ev.title for ev, _ in parsed.valid)
    assert titles == [
        "Bloom — new food license",
        "Bun Buds - K101 — new food license",
        "Mochi & Brew - K118 — new food license",
        "Rosa's Kitchen - K111 — new food license",
        "Taco Mex — new food license",
        "The Halal Fusion — new food license",
    ]
    bloom = next(ev for ev, _ in parsed.valid if ev.title.startswith("Bloom"))
    # license_add_dt_tm "2026-09-09 16:40:00.293+00" → the local (Boston) calendar date, all day
    assert bloom.start == datetime(2026, 9, 9, 0, 0, tzinfo=ET) and bloom.all_day
    assert bloom.location.lat == 42.353425169987005 and bloom.location.address == "23 Northern, Boston, MA"
    assert bloom.description and bloom.description.startswith("License signal, not a confirmed opening date.")
    # food-hall kiosks at one property stay separate records
    assert len({ev.record_id for ev, _ in parsed.valid}) == 6
    blob = dump(parsed)
    assert "7186667214" not in blob and "dayphn" not in blob  # phone column dropped


def test_boston_discovers_the_current_download_link(tmp_path: Path, settings: Settings) -> None:
    page = (FIXTURES / "boston_food_openings_csv/dataset_page.html").read_bytes()
    t = FixtureTransport()
    t.add("data.boston.gov/robots.txt", (
        "User-agent: *\nDisallow: /api/\nDisallow: /datastore/*\nDisallow: /dataset/activity/*\n"
    ))  # fmt: skip
    t.add(r"/dataset/active-food-establishment-licenses$", page)
    t.add(r"/resource/f1e13724-284d-478c-b8bc-ef042aa5b70b/download/tmppi79touu\.csv$", (FIXTURES / BOS).read_bytes())
    fr = get_adapter("csvfile").fetch(fetch_ctx(unit("boston_food_openings_csv"), client(t, tmp_path), settings))
    assert fr.payloads[0].url.endswith("/download/tmppi79touu.csv")
    assert not any("/api/" in c for c in t.calls)  # never the robots-disallowed CKAN API


def test_robots_disallowed_api_path_is_never_used_by_config() -> None:
    src = unit("boston_food_openings_csv").source
    assert "/api/" not in src.params["url"] and "datastore" not in src.params["url"]
