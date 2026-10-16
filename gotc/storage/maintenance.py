"""State maintenance that keeps the persisted DB bounded at 50–100 cities (SCALING.md §4.5, §4.6 items 7–8).

Price snapshots: full resolution for 72 h (what the "selling fast" / trend signals read), then one row per
(event, seller, UTC day) holding that day's min price_min, max price_max, median listing_count and last
availability, stamped at the day's first observation; rows for events that started more than a day ago are
deleted. Snapshot rows are reported values; the daily rollup keeps reported extremes and never invents a price.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from statistics import median

from gotc.storage.db import Database, iso

FULL_RESOLUTION = timedelta(hours=72)


def downsample_price_snapshots(db: Database, now: datetime) -> tuple[int, int]:
    """→ (rows deleted, daily rows written)."""
    cutoff = iso(now - FULL_RESOLUTION)
    rows = db.all(
        "SELECT source_id, record_id, city, seller, observed_at, price_min, price_max, listing_count, availability"
        " FROM price_snapshots WHERE observed_at < ? ORDER BY source_id, record_id, city, seller, observed_at",
        (cutoff,),
    )
    groups: dict[tuple[str, str, str, str, str], list[dict[str, object]]] = {}
    for r in rows:
        key = (r["source_id"], r["record_id"], r["city"], r["seller"], str(r["observed_at"])[:10])
        groups.setdefault(key, []).append(dict(r))
    deleted = written = 0
    with db.tx():
        for (src, rid, city, seller, _day), snaps in groups.items():
            if len(snaps) == 1:
                continue
            mins = [float(str(s["price_min"])) for s in snaps if s["price_min"] is not None]
            maxs = [float(str(s["price_max"])) for s in snaps if s["price_max"] is not None]
            counts = [int(str(s["listing_count"])) for s in snaps if s["listing_count"] is not None]
            first = snaps[0]
            for s in snaps:
                db.execute(
                    "DELETE FROM price_snapshots WHERE source_id=? AND record_id=? AND city=? AND seller=?"
                    " AND observed_at=?",
                    (src, rid, city, seller, s["observed_at"]),
                )
                deleted += 1
            db.execute(
                "INSERT INTO price_snapshots (source_id, record_id, city, seller, observed_at, price_min, price_max,"
                " listing_count, availability) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    src,
                    rid,
                    city,
                    seller,
                    first["observed_at"],
                    min(mins) if mins else None,
                    max(maxs) if maxs else None,
                    int(median(counts)) if counts else None,
                    snaps[-1]["availability"],
                ),
            )
            deleted -= 1  # the rollup row replaces one of them
            written += 1
        past = db.execute(
            "DELETE FROM price_snapshots WHERE EXISTS (SELECT 1 FROM source_records sr WHERE"
            " sr.source_id = price_snapshots.source_id AND sr.record_id = price_snapshots.record_id"
            " AND sr.city = price_snapshots.city AND sr.start_at < ?)",
            (iso(now - timedelta(days=1)),),
        ).rowcount
    return deleted + max(past, 0), written
