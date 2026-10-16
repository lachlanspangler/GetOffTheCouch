from datetime import UTC, datetime, timedelta

from gotc.pipeline.venue_refs import store_bindings, sync
from tests.conftest import FixtureTransport, fast_client, make_city

NOW = datetime(2026, 10, 16, tzinfo=UTC)
RESP = {
    "results": {
        "bindings": [
            {
                "v": {"value": "http://www.wikidata.org/entity/Q7103968"},
                "vLabel": {"value": "Orpheum Theatre"},
                "capacity": {"value": "2579"},
                "c": {"value": "Point(-93.2756 44.9755)"},
            },
            {
                "v": {"value": "http://www.wikidata.org/entity/Q1"},
                "vLabel": {"value": "Q1"},
                "capacity": {"value": "100"},
            },
            {
                "v": {"value": "http://www.wikidata.org/entity/Q2"},
                "vLabel": {"value": "Band Box"},
                "capacity": {"value": "13"},
            },
        ]
    }
}


def test_sync_never_touches_wikidata(db):
    """query.wikidata.org/robots.txt: Disallow /sparql; www.wikidata.org: Disallow /w/ and /api/ (2026-10-16)."""
    t = FixtureTransport()  # any request at all would raise "unexpected request in test"
    assert sync(db, fast_client(t), make_city(), NOW) == 0
    assert t.calls == []


def test_existing_rows_keep_serving(db):
    assert store_bindings(db, make_city(), RESP, NOW) == 1  # unlabeled + implausibly small rows dropped
    sync(db, fast_client(FixtureTransport()), make_city(), NOW + timedelta(days=30))
    row = db.one("SELECT * FROM venue_refs")
    assert (row["name"], row["capacity"], row["ref_id"], row["lat"]) == (
        "Orpheum Theatre",
        2579,
        "wikidata:Q7103968",
        44.9755,
    )
