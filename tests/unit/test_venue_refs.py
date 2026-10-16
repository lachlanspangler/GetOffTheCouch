from datetime import UTC, datetime, timedelta

from gotc.pipeline.venue_refs import sync
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


def test_sync_stores_capacities_with_qids_and_respects_ttl(db):
    t = FixtureTransport().add(r"query\.wikidata\.org/sparql", RESP)
    assert sync(db, fast_client(t), make_city(), NOW) == 1  # unlabeled + implausibly small rows dropped
    row = db.one("SELECT * FROM venue_refs")
    assert (row["name"], row["capacity"], row["ref_id"], row["lat"]) == (
        "Orpheum Theatre",
        2579,
        "wikidata:Q7103968",
        44.9755,
    )
    assert sync(db, fast_client(t), make_city(), NOW + timedelta(days=1)) == 0  # cached for a week
    assert len(t.calls) == 1


def test_outage_keeps_previous_rows(db):
    sync(db, fast_client(FixtureTransport().add(r"wikidata", RESP)), make_city(), NOW)
    down = FixtureTransport().add(r"wikidata", status=503)
    assert sync(db, fast_client(down), make_city(), NOW + timedelta(days=8)) == 0
    assert db.one("SELECT COUNT(*) c FROM venue_refs")["c"] == 1
