"""Sharded refresh (SCALING.md §4.6 item 3): shards fetch disjoint cities from the same base DB, export deltas,
and the publish job's merge + build reproduces what one monolithic run would have produced."""

import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from gotc.pipeline.run import run
from gotc.settings import Settings
from gotc.storage import delta
from gotc.storage.db import Database
from tests.conftest import NOW, fast_client, make_city, make_registry
from tests.integration.test_pipeline import ICS, TRIBE, healthy_transport

MPLS = make_city("minneapolis", [TRIBE])
TESTVILLE = make_city("testville", [ICS])
REG = make_registry(MPLS, TESTVILLE)
LATER = NOW + timedelta(hours=25)  # every unit is due again


def settings_for(tmp: Path, name: str) -> Settings:
    docs = tmp / name / "docs"
    docs.mkdir(parents=True)
    (docs / "DIARY.md").write_text("# Diary\n")
    return Settings(data_dir=tmp / name / "data", web_data_dir=tmp / name / "web", docs_dir=docs)


def snapshot(db: Database) -> dict[str, object]:
    return {
        "records": sorted(
            (r["unit"], r["record_id"], r["content_hash"], r["gone_at"]) for r in db.all("SELECT * FROM source_records")
        ),
        "health": sorted(
            (r["unit"], r["state"], r["consecutive_successes"], r["last_success_at"])
            for r in db.all("SELECT * FROM unit_health")
        ),
        "events": sorted((r["city"], r["id"], r["start_at"]) for r in db.all("SELECT city, id, start_at FROM events")),
        "raw": db.one("SELECT COUNT(*) c FROM raw_fetches")["c"],
        "run_units": db.one("SELECT COUNT(*) c FROM run_units")["c"],
    }


@pytest.fixture
def base(tmp_path: Path) -> Path:
    s = settings_for(tmp_path, "base")
    db = Database(s.db_path)
    run(db, REG, s, client=fast_client(healthy_transport()), now=NOW, geocode=False)
    db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db.close()
    return s.db_path


def copy_db(base: Path, tmp: Path, name: str) -> tuple[Database, Settings]:
    s = settings_for(tmp, name)
    s.db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(base, s.db_path)
    return Database(s.db_path), s


def test_shards_plus_publish_equal_a_monolithic_run(base: Path, tmp_path: Path):
    mono, ms = copy_db(base, tmp_path, "mono")
    run(mono, REG, ms, client=fast_client(healthy_transport()), now=LATER, geocode=False)

    deltas = []
    for city in ("minneapolis", "testville"):
        db, s = copy_db(base, tmp_path, f"shard_{city}")
        mark = delta.mark(db, NOW + timedelta(hours=24))
        rep = run(db, REG, s, client=fast_client(healthy_transport()), now=LATER, geocode=False, cities=[city],
                  build=False, trigger="shard")  # fmt: skip
        assert {u.unit.split("@")[1] for u in rep.units} == {city} and not rep.builds
        db.close()
        out = tmp_path / f"{city}.delta.db"
        counts = delta.export_delta(s.db_path, mark, [city], out)
        assert counts["runs"] == 1 and counts["source_records"] > 0
        deltas.append(out)

    pub, ps = copy_db(base, tmp_path, "publish")
    expect = delta.mark(pub)
    for d in deltas:
        delta.merge_delta(pub, d, expect)
    rep = run(pub, REG, ps, client=fast_client(healthy_transport()), now=LATER, geocode=False, fetch=False,
              trigger="publish")  # fmt: skip
    assert not rep.units and {b.city for b in rep.builds} == {"minneapolis", "testville"}

    a, b = snapshot(mono), snapshot(pub)
    assert a["records"] == b["records"]
    assert a["health"] == b["health"]
    assert a["events"] == b["events"]
    assert a["raw"] == b["raw"]
    # every merged source record points at a raw_fetches row that exists (ids were remapped)
    orphans = pub.one(
        "SELECT COUNT(*) c FROM source_records sr WHERE raw_fetch_id IS NOT NULL AND NOT EXISTS"
        " (SELECT 1 FROM raw_fetches rf WHERE rf.id = sr.raw_fetch_id)"
    )
    assert orphans["c"] == 0
    assert (ps.web_data_dir / "cities" / "testville.json").exists()


def test_delta_from_another_base_is_refused(base: Path, tmp_path: Path):
    db, s = copy_db(base, tmp_path, "shard")
    mark = delta.mark(db)
    run(db, REG, s, client=fast_client(healthy_transport()), now=LATER, geocode=False, cities=["testville"],
        build=False)  # fmt: skip
    db.close()
    out = tmp_path / "t.delta.db"
    delta.export_delta(s.db_path, mark, ["testville"], out)
    pub, _ = copy_db(base, tmp_path, "publish")
    run(pub, REG, _, client=fast_client(healthy_transport()), now=LATER, geocode=False)  # publish DB moved on
    with pytest.raises(delta.DeltaMismatch):
        delta.merge_delta(pub, out, delta.mark(pub))


def test_plan_shards_balances_unit_counts():
    shards = delta.plan_shards({"a": 20, "b": 18, "c": 5, "d": 4, "e": 3}, size=3)
    assert len(shards) == 2
    assert sorted(c for s in shards for c in s) == ["a", "b", "c", "d", "e"]
    assert {"a", "b"} not in [set(s) for s in shards]  # the two big cities land in different shards
    assert delta.plan_shards({}, 4) == []


def test_bad_slugs_never_reach_sql(tmp_path: Path):
    with pytest.raises(ValueError):
        delta.export_delta(tmp_path / "x.db", {"runs": 0}, ["x'); DROP TABLE runs; --"], tmp_path / "o.db")


def test_city_filter_is_exact_not_a_like_pattern():
    import sqlite3

    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE t (unit TEXT)")
    con.executemany("INSERT INTO t VALUES (?)", [("a@new_orleans",), ("b@newXorleans",), ("c@x@new_orleans",)])
    rows = con.execute(f"SELECT unit FROM t WHERE {delta._like(['new_orleans'])} ORDER BY unit").fetchall()
    assert rows == [("a@new_orleans",)]
