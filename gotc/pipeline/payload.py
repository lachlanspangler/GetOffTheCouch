"""Per-city payload budgets (SCALING.md §4.6 item 5). Checked by `gotc validate` and the contract tests.

The budgets are for what a visitor downloads on first paint:
  * the next-14-days slice of a city's card feed: warn above 1.5 MB raw or 250 KB gzip, but only for a city
    without week shards (I-117, ADR-0009); sharded first views are budgeted in web/scripts/check-budgets.mjs
  * the whole card feed: warn above 5 MB raw, **fail above 8 MB raw** (the doc's "do item 5 before NYC passes
    ~8 MB" trigger); the details file: fail above 4 MB raw
Nothing is ever dropped to meet a budget here; failing the budget fails the check so a human decides.
"""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

MB = 1_000_000
NOW_RAW_WARN = 1.5 * MB
NOW_GZ_WARN = 250_000
CARDS_RAW_WARN = 5 * MB
CARDS_RAW_FAIL = 8 * MB
DETAILS_RAW_FAIL = 4 * MB


@dataclass
class PayloadReport:
    city: str
    cards_raw: int
    details_raw: int
    now_raw: int
    now_gz: int
    warnings: list[str]
    failures: list[str]


def _now_slice(doc: dict[str, object], now: datetime) -> bytes:
    horizon = now + timedelta(days=14)
    events = doc.get("events") or []
    keep = []
    for e in events if isinstance(events, list) else []:
        try:
            start = datetime.fromisoformat(str(e["start"]).replace("Z", "+00:00"))
            end = datetime.fromisoformat(str(e.get("end") or e["start"]).replace("Z", "+00:00"))
        except (KeyError, ValueError, TypeError):
            continue
        if end >= now - timedelta(hours=3) and start <= horizon:
            keep.append(e)
    return json.dumps({**doc, "events": keep}, separators=(",", ":")).encode()


def check_city(cards: Path, now: datetime) -> PayloadReport:
    details = cards.with_name(cards.stem + ".details.json")
    raw = cards.read_bytes()
    doc = json.loads(raw)
    now_slice = _now_slice(doc, now)
    rep = PayloadReport(
        city=cards.stem,
        cards_raw=len(raw),
        details_raw=details.stat().st_size if details.exists() else 0,
        now_raw=len(now_slice),
        now_gz=len(gzip.compress(now_slice, 6)),
        warnings=[],
        failures=[],
    )
    sharded = (cards.parent / cards.stem / "manifest.json").exists()  # I-117: browsers load week shards instead
    if not sharded and (rep.now_raw > NOW_RAW_WARN or rep.now_gz > NOW_GZ_WARN):
        rep.warnings.append(
            f"{rep.city}: next-14-days cards {rep.now_raw / MB:.2f} MB raw / {rep.now_gz / 1000:.0f} KB gz "
            f"(budget {NOW_RAW_WARN / MB:.1f} MB / {NOW_GZ_WARN / 1000:.0f} KB): time for week-sharded card files"
        )
    if rep.cards_raw > CARDS_RAW_FAIL:
        rep.failures.append(f"{rep.city}: card feed {rep.cards_raw / MB:.1f} MB raw > {CARDS_RAW_FAIL / MB:.0f} MB")
    elif rep.cards_raw > CARDS_RAW_WARN:
        rep.warnings.append(f"{rep.city}: card feed {rep.cards_raw / MB:.1f} MB raw > {CARDS_RAW_WARN / MB:.0f} MB")
    if rep.details_raw > DETAILS_RAW_FAIL:
        rep.failures.append(f"{rep.city}: details {rep.details_raw / MB:.1f} MB raw > {DETAILS_RAW_FAIL / MB:.0f} MB")
    return rep


def check_all(web_data_dir: Path, now: datetime) -> list[PayloadReport]:
    cities = web_data_dir / "cities"
    if not cities.is_dir():
        return []
    return [check_city(p, now) for p in sorted(cities.glob("*.json")) if not p.name.endswith(".details.json")]
