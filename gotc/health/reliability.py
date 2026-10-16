"""Measured source reliability (I-071): from run history, not vibes.

score = 100 × success_rate × (1 − reject_rate)   over the last 30 days of attempts
  * success_rate: fraction of attempts with status ok (disabled/skipped attempts don't count)
  * reject_rate:  rejected / (valid + rejected) across those attempts
Grades: A ≥ 95 · B ≥ 85 · C ≥ 70 · D below · "–" with fewer than 3 attempts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from gotc.storage.db import Database, iso


@dataclass(frozen=True)
class Reliability:
    unit: str
    attempts: int
    success_rate: float
    reject_rate: float
    score: float | None
    grade: str


def grade(score: float | None) -> str:
    if score is None:
        return "–"
    return "A" if score >= 95 else "B" if score >= 85 else "C" if score >= 70 else "D"


def reliability(db: Database, now: datetime, days: int = 30) -> dict[str, Reliability]:
    rows = db.all(
        "SELECT unit, COUNT(*) n, SUM(status = 'ok') ok, SUM(valid) v, SUM(rejected) r FROM run_units"
        " WHERE started_at >= ? AND status IN ('ok', 'failed') GROUP BY unit",
        (iso(now - timedelta(days=days)),),
    )
    out: dict[str, Reliability] = {}
    for r in rows:
        n, ok, v, rej = int(r["n"]), int(r["ok"] or 0), int(r["v"] or 0), int(r["r"] or 0)
        sr = ok / n if n else 0.0
        rr = rej / (v + rej) if v + rej else 0.0
        score = round(100 * sr * (1 - rr), 1) if n >= 3 else None
        out[r["unit"]] = Reliability(r["unit"], n, round(sr, 3), round(rr, 3), score, grade(score))
    return out
