"""config/metros.yaml (SCALING.md §1 top-50), Census re-centering, and `gotc city new`."""

from gotc.metros import load_metros, metros, recenter, same_street
from tests.conftest import FixtureTransport, fast_client

ROW = """metros:
  - rank: 10
    cbsa: "38060"
    msa: "Phoenix-Mesa-Chandler"
    msa_pop_m: 5.19
    name: "Phoenix"
    state: AZ
    slug: phoenix
    timezone: America/Phoenix
    center: [33.4484, -112.0740]
    center_source: scaling_md
    center_address: "200 W Washington St, Phoenix, AZ 85003"
    radius_km: 30
"""


def census(street: str, x: float, y: float) -> dict:
    return {"result": {"addressMatches": [{"matchedAddress": street, "coordinates": {"x": x, "y": y}}]}}


def test_table_has_the_top_50_and_the_ten_incumbents():
    m = metros()
    assert len(m) == 50 and sorted(x.rank for x in m.values()) == list(range(1, 51))
    assert {s for s, x in m.items() if x.incumbent} == {
        "nyc", "los_angeles", "chicago", "miami", "boston", "seattle", "minneapolis", "denver", "austin", "nashville",
    }  # fmt: skip
    assert m["phoenix"].cbsa == "38060" and m["phoenix"].timezone == "America/Phoenix"


def test_same_street_rejects_wrong_direction_or_number():
    assert same_street("200 W Washington St, Phoenix", "200 W WASHINGTON ST, PHOENIX, AZ, 85003")
    assert not same_street("260 Broadway, New York", "260 E BROADWAY, NEW YORK, NY, 10002")
    assert not same_street("200 N Spring St, LA", "200 S SPRING ST, LOS ANGELES, CA, 90012")
    assert not same_street("201 Main St", "200 MAIN ST")


def test_recenter_rewrites_only_verified_rows(tmp_path):
    path = tmp_path / "metros.yaml"
    path.write_text(ROW)
    t = FixtureTransport().add(r"onelineaddress", census("200 W WASHINGTON ST, PHOENIX, AZ, 85003", -112.0764, 33.4483))
    log = recenter(path, fast_client(t))
    m = load_metros(path)["phoenix"]
    assert m.center == (33.4483, -112.0764) and m.center_source == "census_geocoder"
    assert m.center_matched == "200 W WASHINGTON ST, PHOENIX, AZ, 85003" and "shift" in log[0]
    # a match far away (or on another street) is rejected and the table value kept
    path.write_text(ROW)
    far = FixtureTransport().add(r"onelineaddress", census("200 W WASHINGTON ST, PHOENIX, AZ, 85003", -111.9, 33.6))
    assert "km from the table center" in recenter(path, fast_client(far))[0]
    assert load_metros(path)["phoenix"].center_source == "scaling_md"


def test_city_new_writes_a_disabled_skeleton(tmp_path, monkeypatch):
    from gotc import cli
    from gotc.config import CityConfig, load_yaml

    monkeypatch.setattr("gotc.settings.CONFIG_DIR", tmp_path)
    (tmp_path / "cities").mkdir()
    (tmp_path / "cities" / "phoenix.yaml").write_text("x")
    assert cli.main(["city", "new", "phoenix"]) == 1  # never overwrites by accident
    assert cli.main(["city", "new", "fresno"]) == 0
    city = CityConfig.model_validate(load_yaml((tmp_path / "cities" / "fresno.yaml").read_text()))
    assert city.enabled is False and city.cbsa == "23420" and city.sources == []
