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
