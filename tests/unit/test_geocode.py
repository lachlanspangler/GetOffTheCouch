from gotc.pipeline.geocode import Geocoder, variants
from tests.conftest import FixtureTransport, fast_client, make_city


def test_variants_strip_system_prefix():
    v = variants("Miami-Dade Public Library – West Kendall Regional", make_city())
    assert v[1].startswith("West Kendall Regional Library")


def test_census_batch_parses_matches_and_caches(db):
    csv_resp = (
        '"0","1434 S. Loomis, Testville, MN, 60608","Match","Exact","1434 S LOOMIS ST, TESTVILLE, MN, 60608","-93.2600,44.9700","1","L"\n'
        '"1","99 Nowhere Rd, Testville, MN","No_Match"\n'
    )
    t = FixtureTransport().add(r"addressbatch", csv_resp)
    g = Geocoder(db, fast_client(t))
    hits = g.batch(["1434 S. Loomis, 60608", "99 Nowhere Rd", "Central Park"], make_city())
    assert hits == 1
    assert len(t.calls) == 1  # one POST for the whole city; place names aren't sent
    hit = g.geocode("1434 S. Loomis, 60608", make_city())
    assert hit and hit.provider == "census_batch" and abs(hit.lat - 44.97) < 1e-6


def test_variants_drop_room_parentheticals():
    v = variants("Seattle Public Library – Northgate Branch (Meeting Room)", make_city())
    assert any(x.startswith("Northgate Branch Library") for x in v)


# ── Nominatim compliance (OSMF usage policy: ≤ 4 req/min for recurring scripts, cache, never repeat) ──

NOMI_HIT = [{"lat": "44.98", "lon": "-93.27", "display_name": "Orpheum Theatre", "addresstype": "amenity"}]


def _nominatim_calls(t: FixtureTransport) -> list[str]:
    return [u for u in t.calls if "nominatim" in u and not u.endswith("/robots.txt")]


def test_nominatim_is_off_by_default(db, monkeypatch):
    monkeypatch.delenv("GOTC_NOMINATIM", raising=False)
    t = FixtureTransport().add(r"nominatim", NOMI_HIT)
    g = Geocoder(db, fast_client(t))
    assert g.geocode("Orpheum Theatre", make_city()) is None
    assert not _nominatim_calls(t), "robots.txt disallows /search; Nominatim is opt-in only"


def test_nominatim_opt_in_is_throttled_to_four_per_minute(db):
    t = FixtureTransport().add(r"nominatim", [])
    c = fast_client(t)
    sleeps: list[float] = []
    c._sleep = sleeps.append
    g = Geocoder(db, c, nominatim=True, nominatim_budget=10)
    assert c.host_intervals["nominatim.openstreetmap.org"] >= 15.0
    for name in ("Alpha Hall", "Bravo Hall", "Charlie Hall"):
        g.geocode(name, make_city())
    assert len(_nominatim_calls(t)) == 3
    # every request after the first waited (almost) the whole 15 s interval
    assert len([s for s in sleeps if s > 14.0]) >= 2


def test_nominatim_interval_cannot_be_loosened(db):
    c = fast_client(FixtureTransport())
    c.host_intervals["nominatim.openstreetmap.org"] = 1.1
    Geocoder(db, c, nominatim=True)
    assert c.host_intervals["nominatim.openstreetmap.org"] == 15.0


def test_nominatim_hard_budget_per_run_across_cities(db):
    t = FixtureTransport().add(r"nominatim", [])
    g = Geocoder(db, fast_client(t), nominatim=True, nominatim_budget=2)
    for i in range(5):
        g.geocode(f"Some Plaza {chr(65 + i)}", make_city())
    g.lookups = 0  # build_city resets the per-city Census budget; the Nominatim budget must not reset
    g.geocode("Another Plaza", make_city("minneapolis"))
    assert len(_nominatim_calls(t)) == 2


def test_nominatim_answers_cached_forever_and_never_repeated(db):
    from datetime import timedelta

    from gotc.storage.db import iso, utcnow

    t = FixtureTransport().add(r"nominatim", [])
    g = Geocoder(db, fast_client(t), nominatim=True, nominatim_budget=50)
    assert g.geocode("Nowhere Pavilion", make_city()) is None
    # long after the Census miss TTL, a query Nominatim already answered is still not sent again
    db.execute("UPDATE geocode_cache SET looked_up_at = ?", (iso(utcnow() - timedelta(days=400)),))
    Geocoder(db, fast_client(t), nominatim=True, nominatim_budget=50).geocode("Nowhere Pavilion", make_city())
    assert len(_nominatim_calls(t)) == 1
    assert db.one("SELECT provider FROM geocode_cache")["provider"] == "none:nominatim"


def test_census_first_then_nominatim_only_for_misses(db):
    census_hit = {
        "result": {"addressMatches": [{"coordinates": {"x": -93.26, "y": 44.97}, "matchedAddress": "1 MAIN ST"}]}
    }
    t = FixtureTransport().add(r"onelineaddress", census_hit).add(r"nominatim", NOMI_HIT)
    g = Geocoder(db, fast_client(t), nominatim=True)
    hit = g.geocode("1 Main St", make_city())
    assert hit and hit.provider == "census"
    assert not _nominatim_calls(t)
    place = g.geocode("Orpheum Theatre", make_city())
    assert place and place.provider == "nominatim"
