"""The gate measured against the golden set (ADR-0010): ≥200 real listings from many metros, labelled blind to the
rules. Positive class = not a real public event. A rule change that starts eating real events (precision) or
letting non-events through (recall) fails here. Current numbers are printed and recorded in NON_EVENTS_AUDIT.md."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

import yaml

from gotc.config import load_registry
from gotc.pipeline.listing_gate import listing_gate
from gotc.reports import GOLDEN_FILE
from gotc.schema import SourceEvent

NOW = datetime(2026, 11, 2, tzinfo=UTC)
MIN_PRECISION = 0.95  # of what we hold back, how much really isn't an event
MIN_RECALL = 0.85  # of the non-events, how many we catch


def score() -> tuple[dict[str, int], list[tuple[str, dict, object]]]:
    items = yaml.safe_load(GOLDEN_FILE.read_text())
    sources = load_registry().all_sources()
    gate = listing_gate()
    c: Counter[str] = Counter()
    misses = []
    for it in items:
        ev = SourceEvent.model_validate(
            {
                "source_id": it["source_id"],
                "record_id": it["id"],
                "city": it["city"],
                "title": it["title"],
                "description": it.get("description"),
                "category": it.get("category", "other.uncategorized"),
                "category_basis": it.get("category_basis"),
                "source_categories": it.get("labels", []),
                "start": NOW,
                "timezone": "UTC",
                "fetched_at": NOW,
            }
        )
        src = sources.get(it["source_id"])
        v = gate.evaluate(ev, src.params if src else {}, src.data_type.value if src else None)
        held, non_event = not v.keep, it["label"] == "not_event"
        key = {(True, True): "tp", (True, False): "fp", (False, True): "fn", (False, False): "tn"}[(held, non_event)]
        c[key] += 1
        if key in ("fp", "fn"):
            misses.append((key, it, v))
    return dict(c), misses


def test_golden_set_is_big_and_spread_across_metros():
    items = yaml.safe_load(GOLDEN_FILE.read_text())
    assert len(items) >= 200
    assert len({i["city"] for i in items}) >= 30 and len({i["source_id"] for i in items}) >= 80
    assert {i["label"] for i in items} == {"event", "not_event"}
    assert len({i["id"] for i in items}) == len(items)


def test_gate_precision_and_recall_on_the_golden_set(capsys):
    c, misses = score()
    precision = c.get("tp", 0) / max(1, c.get("tp", 0) + c.get("fp", 0))
    recall = c.get("tp", 0) / max(1, c.get("tp", 0) + c.get("fn", 0))
    with capsys.disabled():
        print(
            f"\nlisting gate on {sum(c.values())} golden listings: precision {precision:.3f}, recall {recall:.3f} {c}"
        )
    detail = "\n".join(
        f"{k} {it['id']} {it['source_id']}: {it['title'][:70]} ({it['why']}) → {v.rule}" for k, it, v in misses
    )
    assert precision >= MIN_PRECISION, detail
    assert recall >= MIN_RECALL, detail
