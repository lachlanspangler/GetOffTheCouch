"""`gotc discover`: parsers from recorded responses (tests/fixtures/discover/, 2026-10-16) + the engine's
politeness rules (robots first, denylist before any request, Cloudflare hard-exclude, request budget)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from gotc.config import CityConfig
from gotc.discover import parse as dp
from gotc.discover.engine import Denylist, Discoverer, Seed, parse_seed, score, write_candidates
from tests.conftest import FIXTURES, FixtureTransport, fast_client

D = FIXTURES / "discover"
NOW = datetime(2026, 10, 16, 20, 0, tzinfo=UTC)
PHOENIX = CityConfig(
    slug="phoenix",
    name="Phoenix",
    state="AZ",
    timezone="America/Phoenix",
    center=(33.4483, -112.0764),
    radius_km=30,
    enabled=False,
)


def text(name: str) -> str:
    return (D / name).read_text()


def js(name: str):
    return json.loads((D / name).read_text())


# ── parsers ───────────────────────────────────────────────────────────────────────────────────────


def test_socrata_catalog_keeps_place_and_state_tenants_only():
    got = dp.socrata_catalog(js("socrata_catalog_liquor_license.json"), ["Denver"], "CO")
    assert got and {d.domain for d in got} == {"data.colorado.gov"}
    assert all(d.columns for d in got)
    assert "htyp-tqzh" in {d.id for d in got}  # the dataset we use for Denver today: discovery finds it
    # non-US tenants (data.novascotia.ca) never pass, whatever the query
    everything = dp.socrata_catalog(js("socrata_catalog_liquor_license.json"), ["Nova Scotia"], "NS")
    assert not [d for d in everything if d.domain.endswith(".ca")]


def test_guess_socrata_fields_refuses_renewal_dates():
    cols = ["license_number", "dba_name", "renewal_date", "license_start_date", "latitude", "longitude", "address"]
    f = dp.guess_socrata_fields(cols)
    assert f == {"start": "license_start_date", "title": "dba_name", "lat": "latitude", "lon": "longitude",
                 "address": "address"}  # fmt: skip
    assert "start" not in dp.guess_socrata_fields(["renewal_issue_date", "expiration_date"])


def test_datagov_search_drops_federal_noise():
    assert dp.datagov_search(js("datagov_search_phoenix_events.json"), ["Phoenix"]) == []


def test_hub_sites_need_the_place_name():
    sites = dp.hub_sites(js("hub_sites_philadelphia.json"), ["Philadelphia"])
    assert sites[0].org_id == "fLeGjb7u4uXqeF9q" and sites[0].source == "City of Philadelphia"
    phx = dp.hub_sites(js("hub_sites_phoenix.json"), ["Phoenix"])
    assert not phx  # Phoenix's search returns CAP, Maricopa County, … none named Phoenix
    county = dp.hub_sites(js("hub_sites_phoenix.json"), ["Phoenix", "Maricopa County", "Maricopa"])
    assert [s.org_id for s in county] == ["ykpntM6e3tHvzKRJ"]  # the county term (Census context) finds it


def test_arcgis_search_and_layer_fields():
    items = dp.arcgis_search(js("arcgis_search_philadelphia.json"))
    assert len(items) == 50 and all(i.url and i.url.startswith("https://services") for i in items)
    assert any(i.name == "Community_Events" for i in items)
    layer = dp.arcgis_layer(js("arcgis_layer_community_events.json"))
    assert layer and layer["date_fields"][:2] == ["START_DATE", "END_DATE"]
    assert dp.arcgis_layer({"error": {"code": 400}}) is None


def test_census_county():
    assert dp.census_county(js("census_geographies_phoenix.json")) == "Maricopa County"
    assert dp.census_county({"result": {"addressMatches": []}}) is None


def test_fingerprints():
    home = dp.fingerprint(text("phoenixpubliclibrary_home.html"), "https://www.phoenixpubliclibrary.org")
    assert home.platforms == {"event_host": ["https://calendar.phoenixpubliclibrary.org"]}
    root = dp.fingerprint(text("libcal_phoenix_root.html"), "https://calendar.phoenixpubliclibrary.org")
    assert "libcal" in root.platforms
    cal = dp.fingerprint(text("libcal_phoenix_calendar.html"), "https://calendar.phoenixpubliclibrary.org/calendar")
    assert cal.platforms["libcal_cid"][0] == "15420" and len(cal.platforms["libcal_cid"]) > 20
    mcl = dp.fingerprint(text("mcldaz_home.html"), "https://mcldaz.org")
    assert mcl.platforms.get("event_host") == ["https://events.mcldaz.org"]
    trumba = dp.fingerprint('<script src="https://www.trumba.com/scripts/spuds.js"></script>'
                            '<script>$Trumba.addSpud({webName: "sea_campus", spudType: "main"});</script>', "x")  # fmt: skip
    assert trumba.platforms["trumba"] == ["sea_campus"]
    bc = dp.fingerprint('<a href="https://hclib.bibliocommons.com/v2/events">x</a> gateway.bibliocommons.com', "x")
    assert bc.platforms["bibliocommons"] == ["hclib"]
    ld = '<script type="application/ld+json">{"@graph":[{"@type":"MusicEvent"},{"@type":"Place"}]}</script>'
    assert dp.fingerprint(ld, "x").jsonld_events == 1


def test_cloudflare_challenge_detected():
    page = "<!DOCTYPE html><html><head><title>Just a moment...</title></head><body>challenge-platform</body></html>"
    assert dp.fingerprint(page, "x").cloudflare
    assert dp.is_cloudflare_challenge(page)
    assert not dp.is_cloudflare_challenge(text("mcldaz_home.html"))


def test_feed_probes():
    ics = dp.ics_events(text("libcal_phoenix.ics"))
    assert ics.ok and ics.items == 6 and ics.title == "Acacia Library"
    xf = dp.carbonhouse_rss(text("carbonhouse_xfinity.xml"))
    assert xf.ok and xf.items == 5 and xf.note is None and xf.title == "Xfinity Mobile Arena"
    bad = dp.galaxy_rss(text("galaxy_bad_domain.xml"))
    assert not bad.ok and "Bad Domain" in (bad.note or "")
    good = dp.galaxy_rss((FIXTURES / "handson_twin_cities" / "payload_0.xml").read_text())
    assert good.ok and good.items >= 10
    bc = dp.bibliocommons_rss((FIXTURES / "hclib_events" / "payload_0.xml").read_text())
    assert bc.ok and bc.items > 0
    spl = dp.trumba_events(json.loads((FIXTURES / "spl_events" / "payload_0.json").read_text()))
    assert spl.ok and spl.items > 0
    mdpls = dp.communico_events(json.loads((FIXTURES / "mdpls_events" / "payload_0.json").read_text()))
    assert mdpls.ok and mdpls.places
    tribe = dp.tribe_events(json.loads((FIXTURES / "mprb_events" / "payload_0.json").read_text()))
    assert tribe.ok and tribe.items > 0
    assert dp.wp_has_tribe({"namespaces": ["wp/v2", "tribe/events/v1"]}) and not dp.wp_has_tribe({"namespaces": []})


def test_volo_teamtrivia_challenge():
    assert dp.volo_ways_to_play(text("volo_phoenix.html")) in (0, None)
    assert dp.volo_ways_to_play((FIXTURES / "volo_boston" / "payload_0.html").read_text()) == 91
    assert "philadelphia" in dp.volo_markets(text("volo_discover.html"))
    regions = dp.teamtrivia_regions(text("teamtrivia_sitemap_locations.xml"))
    assert dp.match_region(regions, "Phoenix", "AZ", []) == "phoenix-tempe"
    assert dp.match_region(regions, "Philadelphia", "PA", []) is None
    metros = dp.challenge_metros(js("challenge_shows_sample.json"), PHOENIX.center, PHOENIX.radius_km)
    assert metros and set(metros) == {"phoenix"}  # the Austin shows are outside the radius


def test_score_weights():
    total, parts = score(True, 1.0, True, True, ["leagues"], {"leagues"}, True, True)
    assert total == 1.0 and parts["works"] == 0.30
    low, _ = score(False, None, False, None, [], set(), False, False)
    assert low == 0.18  # half credit for unmeasured geo + freshness, a little for value


def test_parse_seed():
    assert parse_seed("library=https://x.org") == Seed("library", "https://x.org")
    assert parse_seed("https://www.asu.edu").kind == "university"
    assert parse_seed("https://example.com").kind == "other"


# ── engine ────────────────────────────────────────────────────────────────────────────────────────


def phoenix_transport() -> FixtureTransport:
    t = FixtureTransport()
    t.add(r"blocked\.example/robots\.txt", "User-agent: *\nDisallow: /\n")
    t.add(r"phoenixpubliclibrary\.org/robots\.txt", "User-agent: *\nAllow: /\n")
    t.add(r"^https://www\.phoenixpubliclibrary\.org/?$", text("phoenixpubliclibrary_home.html"))
    t.add(r"^https://calendar\.phoenixpubliclibrary\.org/?$", text("libcal_phoenix_root.html"))
    t.add(r"calendar\.phoenixpubliclibrary\.org/calendar$", text("libcal_phoenix_calendar.html"))
    t.add(r"ical_subscribe\.php", text("libcal_phoenix.ics"))
    t.add(r"gateway\.bibliocommons\.com", status=404)
    t.add(r"cf\.example/robots\.txt", "User-agent: *\nAllow: /\n")
    t.add(r"cf\.example", "<html><title>Just a moment...</title>challenge-platform</html>", status=403)
    t.add(r"volosports\.com/discover/phoenix", text("volo_phoenix.html"))
    t.add(r"volosports\.com/discover", text("volo_discover.html"))
    t.add(r"teamtrivia\.com/sitemap-locations", text("teamtrivia_sitemap_locations.xml"))
    t.add(r"challengeentertainment\.com", js("challenge_shows_sample.json"))
    return t


def test_discover_end_to_end_from_fixtures(tmp_path: Path):
    t = phoenix_transport()
    d = Discoverer(
        PHOENIX,
        fast_client(t),
        NOW,
        seeds=[
            Seed("library", "https://www.phoenixpubliclibrary.org"),
            Seed("library", "https://blocked.example/"),
            Seed("venue", "https://cf.example/"),
            Seed("venue", "https://www.livenation.com/venue/phoenix"),
        ],
        families=("library", "venue", "leagues", "trivia"),
        denylist=Denylist(hosts=["livenation.com"], markers=["Live Nation Entertainment"]),
    )
    doc = d.run()
    ids = {c["unit"]["id"]: c for c in doc["candidates"]}
    libcal = ids["phoenix_calendar_phoenixpubliclibrary_libcal"]
    assert libcal["unit"]["adapter"] == "ics" and libcal["unit"]["enabled"] is False
    assert len(libcal["unit"]["params"]["url"]) > 20  # one ICS per public calendar
    assert libcal["evidence"]["robots"]["verdict"] == "allowed"
    assert "phoenix_teamtrivia" in ids and ids["phoenix_teamtrivia"]["unit"]["params"]["regions"] == {
        "phoenix": "phoenix-tempe"
    }
    assert ids["phoenix_challenge_trivia"]["unit"]["params"]["metros"] == ["phoenix"]
    reasons = {x["excluded"] for x in doc["excluded"]}
    assert {"robots_disallowed", "cloudflare", "tos_denylist", "no_market"} <= reasons
    assert not [u for u in t.calls if "livenation" in u], "denylisted hosts are never requested"
    assert not [u for u in t.calls if "blocked.example" in u and not u.endswith("robots.txt")]
    assert doc["candidates"] == sorted(doc["candidates"], key=lambda c: -c["confidence"])
    out = tmp_path / "phoenix.yaml"
    write_candidates(doc, out)
    assert out.read_text().startswith("# gotc discover phoenix")


def test_budget_stops_cleanly():
    d = Discoverer(PHOENIX, fast_client(phoenix_transport()), NOW, families=("leagues", "trivia"), budget=2,
                   denylist=Denylist())  # fmt: skip
    doc = d.run()
    assert doc["requests"]["used"] == 2 and "budget" in (doc["stopped"] or "")


def test_cloudflare_host_is_never_retried():
    t = (
        FixtureTransport()
        .add(r"cf\.example/robots", "")
        .add(r"cf\.example", "<title>Just a moment...</title>", status=403)
    )
    d = Discoverer(PHOENIX, fast_client(t), NOW, families=(), denylist=Denylist())
    assert d.get("https://cf.example/a") is None
    assert d.get("https://cf.example/b") is None
    assert len([u for u in t.calls if not u.endswith("robots.txt")]) == 1


@pytest.mark.parametrize("status", [404, 500])
def test_http_errors_are_logged_not_raised(status):
    t = FixtureTransport().add(r"x\.example", status=status)
    c = fast_client(t)
    c.max_attempts = 1
    d = Discoverer(PHOENIX, c, NOW, families=(), denylist=Denylist())
    assert d.get("https://x.example/") is None
    assert d.probes[-1]["verdict"] == f"http_{status}"


def test_fixture_transport_rejects_unknown_hosts():
    with pytest.raises(AssertionError):
        FixtureTransport().handle_request(httpx.Request("GET", "https://nope.example/"))


def test_cloudflare_on_robots_txt_is_labeled_and_blocks_the_host():
    t = FixtureTransport().add(r"cf\.example", "<title>Just a moment...</title> challenge-platform", status=403)
    d = Discoverer(PHOENIX, fast_client(t), NOW, families=(), denylist=Denylist())
    assert d.get("https://cf.example/page") is None
    assert d.excluded[0]["excluded"] == "cloudflare"
    assert d.excluded[0]["evidence"]["robots"] == "robots_txt_http_403"
    assert t.calls == ["https://cf.example/robots.txt"]  # the page itself was never requested
