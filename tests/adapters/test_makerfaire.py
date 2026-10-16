"""Maker Faire global map JSON against the research sample (live endpoint is Cloudflare-challenged; source disabled)."""

from datetime import UTC, datetime

import pytest

from gotc.adapters.base import FetchContext, ParseContext, Payload, get_adapter
from gotc.adapters.makerfaire import _coord
from gotc.config import CityConfig, SourceConfig, Unit
from gotc.http.client import HttpStatusError
from gotc.pipeline.ingest import parse_payloads
from tests.conftest import FIXTURES, FixtureTransport, fast_client

SRC = SourceConfig(
    id="makerfaire", adapter="makerfaire", name="Maker Faire", data_type="conventions", scope="all_cities"
)
# a city whose center is ~10 km from the Baton Rouge faire, and one (Louisville) given in its own tz
BATON_ROUGE = CityConfig(
    slug="baton_rouge", name="Baton Rouge", state="LA", timezone="America/Chicago", center=(30.4515, -91.1871)
)
LOUISVILLE = CityConfig(
    slug="louisville", name="Louisville", state="KY", timezone="America/New_York", center=(38.2527, -85.7585)
)
MINNEAPOLIS = CityConfig(
    slug="minneapolis", name="Minneapolis", state="MN", timezone="America/Chicago", center=(44.9778, -93.2650)
)
AT = datetime(2026, 10, 15, 18, 0, tzinfo=UTC)


def payload(at: datetime = AT) -> Payload:
    content = (FIXTURES / "makerfaire" / "research_2026-10-15.json").read_bytes()
    return Payload("https://makerfaire.com/query/?type=map", 200, content, at)


def parse(city: CityConfig, at: datetime = AT):
    return parse_payloads(get_adapter("makerfaire"), Unit(source=SRC, city=city), [(payload(at), None)], at)


def test_keeps_only_nearby_public_faires_without_rejects():
    p = parse(BATON_ROUGE)
    assert [ev.title for ev, _ in p.valid] == ["Maker Faire Baton Rouge"] and not p.rejects
    ev = p.valid[0][0]
    assert ev.category == "niche.maker_faire" and ev.all_day
    assert ev.start.isoformat() == "2026-10-17T00:00:00-05:00"
    assert ev.end is not None and ev.end.isoformat() == "2026-10-17T23:59:00-05:00"
    assert str(ev.url) == "https://batonrouge.makerfaire.com/"
    assert ev.location.lat == pytest.approx(30.441399) and ev.location.geocode_method.value == "reported"
    assert ev.extras["distance_km"] < 20
    assert not parse(MINNEAPOLIS).valid  # nothing within the Twin Cities radius


def test_city_timezone_is_used_for_date_only_values():
    ev = parse(LOUISVILLE).valid[0][0]
    assert ev.title == "Maker Faire Louisville"
    assert ev.start.isoformat() == "2026-10-17T00:00:00-04:00"


def test_past_faires_are_dropped():
    assert not parse(BATON_ROUGE, datetime(2026, 11, 1, tzinfo=UTC)).valid


def test_school_faires_are_excluded_by_default():
    src = SRC.model_copy(update={"params": {"categories": ["School"], "max_km": 20000}})
    evs = list(get_adapter("makerfaire").parse(payload(), ParseContext(Unit(source=src, city=BATON_ROUGE), AT)))
    assert [e["title"] for e in evs] == ["CTISM School Maker Faire"]
    assert evs[0]["location"]["lon"] == pytest.approx(-53.71733)  # "-53.71733,17z" → leading number


@pytest.mark.parametrize(("raw", "out"), [("-53.71733,17z", -53.71733), ("", None), ("0", None), ("200", None)])
def test_coord_parsing(raw, out):
    assert _coord(raw, 180) == out


def test_cloudflare_challenge_is_a_typed_forbidden_failure(settings):
    t = (
        FixtureTransport()
        .add(r"robots\.txt$", "User-agent: *\nDisallow: /wp-admin/\n")
        .add(r"/query/", "<html><title>Just a moment...</title></html>", status=403)
    )
    ctx = FetchContext(unit=Unit(source=SRC, city=MINNEAPOLIS), http=fast_client(t), now=AT, settings=settings)
    with pytest.raises(HttpStatusError) as e:
        get_adapter("makerfaire").fetch(ctx)
    assert e.value.kind == "forbidden"
    assert any("type=map" in c for c in t.calls)  # the query string survives (PoliteClient merge fix)
