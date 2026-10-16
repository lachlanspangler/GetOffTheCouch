from datetime import UTC, datetime, timedelta

from gotc.health.reliability import grade, reliability
from gotc.storage.db import iso

NOW = datetime(2026, 10, 16, tzinfo=UTC)


def add(db, run, unit, status, valid=10, rej=0, days_ago=1):
    db.execute("INSERT OR IGNORE INTO runs (id, started_at, status) VALUES (?, ?, 'ok')", (run, iso(NOW)))
    db.execute(
        "INSERT INTO run_units (run_id, unit, status, started_at, valid, rejected) VALUES (?,?,?,?,?,?)",
        (run, unit, status, iso(NOW - timedelta(days=days_ago)), valid, rej),
    )


def test_scores_from_history(db):
    for i in range(4):
        add(db, i, "a@x", "ok")
    add(db, 5, "b@x", "ok", valid=8, rej=2)
    add(db, 6, "b@x", "failed", valid=0)
    add(db, 7, "b@x", "ok")
    add(db, 8, "c@x", "ok")
    add(db, 9, "a@x", "failed", days_ago=60)  # outside the window
    r = reliability(db, NOW)
    assert r["a@x"].score == 100 and r["a@x"].grade == "A"
    assert r["b@x"].success_rate == round(2 / 3, 3) and r["b@x"].grade == "D"
    assert r["c@x"].score is None and r["c@x"].grade == "–"


def test_grades():
    assert [grade(x) for x in (99, 90, 75, 10, None)] == ["A", "B", "C", "D", "–"]
