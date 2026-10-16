"""Luma public calendar ICS feeds through the generic ``ics`` adapter (real recorded feeds)."""

import json
from datetime import datetime

from gotc.adapters.base import Payload, get_adapter
from gotc.config import CityConfig, SourceConfig, Unit
from gotc.pipeline.ingest import parse_payloads
from tests.conftest import FIXTURES

MPLS = CityConfig(
    slug="minneapolis", name="Minneapolis", state="MN", timezone="America/Chicago", center=(44.98, -93.27)
)
BOS = CityConfig(slug="boston", name="Boston", state="MA", timezone="America/New_York", center=(42.36, -71.06))


def run(sid: str, city: CityConfig, name: str = "payload_0.ics", at: datetime | None = None, **params):
    meta = json.loads((FIXTURES / sid / "meta.json").read_text())
    at = at or datetime.fromisoformat(meta["recorded_at"])
    url = next(iter(meta.get("urls", {}).values()), "https://api.lu.ma/ics/get")
    src = SourceConfig(id=sid, adapter="ics", name=sid, data_type="events", params={"url": url, **params})
    p = Payload(url, 200, (FIXTURES / sid / name).read_bytes(), at, "ics")
    return parse_payloads(get_adapter("ics"), Unit(source=src, city=city), [(p, None)], at)


def test_zoma_house_feed():
    parsed = run(
        "luma_zoma_house", MPLS, horizon_days=60, organizer="ZOMA House", default_category="community.cultural"
    )
    assert len(parsed.valid) == 6 and not parsed.rejects  # 45 VEVENTs, 6 upcoming within 60 days
    jam = min((ev for ev, _ in parsed.valid if ev.title == "BIPOC Improv Jam"), key=lambda e: e.start)
    assert jam.start == datetime.fromisoformat("2026-10-18T16:00:00-05:00")  # DTSTART 21:00Z
    assert jam.timezone == "America/Chicago"
    assert jam.category == "nightlife.comedy"  # "improv" keyword beats the default
    assert jam.location.venue_name == "ZOMA House" and jam.location.lat is not None
    assert jam.organizer == "ZOMA House"


def test_research_sample_still_parses():
    parsed = run(
        "luma_zoma_house", MPLS, name="research_2026-10-15.ics", at=datetime.fromisoformat("2026-10-15T18:00:00+00:00")
    )
    assert parsed.valid and not parsed.rejects


def test_hidden_address_url_is_not_a_venue():
    parsed = run("luma_startup_boston", BOS, horizon_days=60, default_category="learning.networking")
    assert parsed.valid and not parsed.rejects
    for ev, _ in parsed.valid:
        assert not (ev.location.venue_name or "").startswith("http")
        assert not (ev.location.address or "").startswith("http")
    hidden = [ev for ev, _ in parsed.valid if ev.location.address is None]
    assert hidden and all(str(ev.url).startswith("https://luma.com/") for ev in hidden)
