from datetime import timedelta

from gotc.storage.db import iso
from gotc.storage.maintenance import downsample_price_snapshots
from tests.conftest import NOW


def snap(db, rid: str, at, lo: float, hi: float, n: int, avail: str = "on_sale") -> None:
    db.execute(
        "INSERT INTO price_snapshots (source_id, record_id, city, seller, observed_at, price_min, price_max,"
        " listing_count, availability) VALUES ('sg', ?, 'testville', 'SeatGeek', ?, ?, ?, ?, ?)",
        (rid, iso(at), lo, hi, n, avail),
    )


def record(db, rid: str, start) -> None:
    db.execute(
        "INSERT INTO source_records (source_id, record_id, city, unit, data, content_hash, start_at, first_seen,"
        " last_seen) VALUES ('sg', ?, 'testville', 'sg@testville', '{}', 'h', ?, ?, ?)",
        (rid, iso(start), iso(NOW), iso(NOW)),
    )


def test_old_snapshots_fold_into_one_row_per_day_recent_stay_hourly(db):
    record(db, "e1", NOW + timedelta(days=20))
    day = NOW - timedelta(days=5)
    for h, (lo, hi, n) in enumerate([(40, 90, 100), (35, 95, 80), (38, 99, 60)]):
        snap(db, "e1", day + timedelta(hours=h), lo, hi, n, "few_left" if h == 2 else "on_sale")
    for h in range(5):  # last 72 h: untouched
        snap(db, "e1", NOW - timedelta(hours=h), 50, 60, 10)
    gone, rolled = downsample_price_snapshots(db, NOW)
    assert (gone, rolled) == (2, 1)
    old = db.all("SELECT * FROM price_snapshots WHERE observed_at < ?", (iso(NOW - timedelta(days=3)),))
    assert len(old) == 1
    r = old[0]
    assert (r["price_min"], r["price_max"], r["listing_count"], r["availability"]) == (35, 99, 80, "few_left")
    assert r["observed_at"] == iso(day)
    assert db.one("SELECT COUNT(*) c FROM price_snapshots")["c"] == 6


def test_snapshots_of_past_events_are_dropped(db):
    record(db, "past", NOW - timedelta(days=3))
    snap(db, "past", NOW - timedelta(days=4), 10, 20, 5)
    gone, _ = downsample_price_snapshots(db, NOW)
    assert gone == 1 and db.one("SELECT COUNT(*) c FROM price_snapshots")["c"] == 0
