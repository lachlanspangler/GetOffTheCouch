"""Freeze a real city feed as a ranking-eval snapshot (RANKING.md §3.1).

    .venv/bin/python scripts/rank_snapshot.py <data_dir> <city> [<city> ...]

Reads <data_dir>/cities/<city>.json (+ .details.json for full descriptions) and <data_dir>/health.json,
computes RankHints with the same code the exporter uses (gotc.pipeline.rankprep), keeps the eval window
(now → now + 7 days, plus league seasons whose registration closes within 30 days), strips fields no
ranker reads, and writes web/tests/rank/fixtures/<city>.feed.json.gz. `now` is the feed's generated_at.
Values are copied, never edited: a snapshot is a trimmed copy of a real export.
"""

from __future__ import annotations

import gzip
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gotc.pipeline.rankprep import annotate  # noqa: E402
from gotc.schema import Event  # noqa: E402

OUT = ROOT / "web" / "tests" / "rank" / "fixtures"
WINDOW = timedelta(days=7)

KEEP = {
    "id", "city", "title", "kind", "category", "categories", "tags", "start", "end", "all_day", "timezone",
    "series_id", "venue_id", "organizer", "is_new", "stale", "first_seen", "last_checked", "rank",
}  # fmt: skip


def trim(e: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in e.items() if k in KEEP}
    loc = e.get("location") or {}
    out["location"] = {k: loc[k] for k in ("venue_name", "lat", "lon", "geocode_confidence") if k in loc}
    p = e.get("price") or {}
    out["price"] = {k: p[k] for k in ("currency", "is_free", "min", "max") if k in p}
    if e.get("url"):
        out["url"] = e["url"]
    if r := e.get("registration"):
        out["registration"] = {
            k: r[k]
            for k in ("closes_at", "early_bird_ends_at", "signup_types", "skill_levels", "method", "confidence")
            if k in r
        }
    if a := e.get("attendance"):
        out["attendance"] = {k: a[k] for k in ("low", "mid", "high", "confidence", "method") if k in a}
        if "reported" in (a.get("inputs") or {}):
            out["attendance"]["inputs"] = {"reported": a["inputs"]["reported"]}
    t = e.get("tickets") or {}
    out["tickets"] = {
        k: t[k] for k in ("availability", "spots_left", "spots_total", "selling_fast", "signal") if k in t
    }
    if s := e.get("social"):
        out["social"] = {"score": s["score"], "reasons": s.get("reasons", [])[:1]}
    if w := e.get("weather"):
        out["weather"] = {k: w[k] for k in ("short", "precip_pct", "source", "fetched_at") if k in w}
    out["offers"] = [{"kind": o["kind"], "availability": o.get("availability", "unknown")} for o in e.get("offers", [])]
    out["sources"] = [{"source_id": s["source_id"]} for s in e.get("sources", [])]
    if e.get("summary"):
        out["summary"] = e["summary"][:160]  # card summary, for labeling and search; ranking uses rank.desc_len
    return out


def in_window(e: Event, now: datetime) -> bool:
    end = e.end or e.start + timedelta(hours=2)
    if e.start <= now + WINDOW and end >= now:
        return True
    r = e.registration
    return e.kind == "season" and r is not None and r.closes_at is not None and now <= r.closes_at <= now + 4 * WINDOW


def main(data_dir: Path, cities: list[str]) -> None:
    health = json.loads((data_dir / "health.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    for city in cities:
        feed = json.loads((data_dir / "cities" / f"{city}.json").read_text())
        details = json.loads((data_dir / "cities" / f"{city}.details.json").read_text())["events"]
        now = datetime.fromisoformat(feed["generated_at"])
        events = []
        for raw in feed["events"]:
            full = {**raw, "summary": details.get(raw["id"], {}).get("summary") or raw.get("summary")}
            full.pop("rank", None)
            events.append(Event.model_validate(full))
        scores = {
            u["source_id"]: (u.get("reliability") or {}).get("score") for u in health["units"] if u["city"] == city
        }
        ranked = annotate(events, scores, now)  # hints over the whole feed (series counts need it)
        cards = {e["id"]: e for e in feed["events"]}
        kept = [
            trim({**cards[e.id], "rank": e.rank.model_dump(exclude_none=True) if e.rank else None})
            for e in ranked
            if in_window(e, now)
        ]
        snap = {
            "city": city,
            "city_name": feed["city_name"],
            "now": feed["generated_at"],
            "schema_version": feed["schema_version"],
            "source": f"web/public/data/cities/{city}.json (generated {feed['generated_at']})",
            "neighborhoods": feed.get("neighborhoods", []),
            "events": kept,
        }
        path = OUT / f"{city}.feed.json.gz"
        path.write_bytes(gzip.compress(json.dumps(snap, separators=(",", ":")).encode(), mtime=0))
        print(f"{city}: {len(kept)} of {len(feed['events'])} events → {path.name} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2:])
