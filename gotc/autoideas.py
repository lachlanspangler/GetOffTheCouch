"""Data-driven idea generation: the pipeline looks at its own output and proposes work.

    python -m gotc.autoideas        # adds new ideas to the ledger (deduped by title), prints them

Heuristics (each produces at most one idea per city/unit, so the ledger doesn't flood):
  * a seed taxonomy family with zero events in a city      → "find a <family> source for <city>"
  * a city with < 3 healthy sources                        → "widen <city> coverage"
  * > 30% of a city's events without coordinates           → "improve geocoding for <city>"
  * a unit with a high reject rate or quarantined          → "fix <unit>"
  * zero deadlines in a city                               → "find registration deadlines for <city>"
"""

from __future__ import annotations

import json
from collections import Counter

from gotc import ideas as ledger
from gotc.config import load_registry
from gotc.health.store import load_health
from gotc.settings import Settings
from gotc.storage.db import Database

CORE = {
    "sports_league": "rec/beer leagues",
    "trivia_games": "trivia nights",
    "volunteer": "volunteering",
    "niche": "cons & faires",
    "music": "concerts",
    "nightlife": "parties & openings",
    "fitness": "run clubs",
}


def propose(db: Database) -> list[tuple[str, str, int, int, str]]:
    reg = load_registry()
    out: list[tuple[str, str, int, int, str]] = []
    for city in reg.cities.values():
        if not city.enabled:
            continue
        rows = db.all("SELECT data FROM events WHERE city = ?", (city.slug,))
        events = [json.loads(r["data"]) for r in rows]
        fams = Counter(e["category"].split(".")[0] for e in events)
        for fam, label in CORE.items():
            if fams.get(fam, 0) == 0:
                out.append(
                    (
                        f"Find a {label} source for {city.name}",
                        "sources",
                        4,
                        2,
                        f"auto: 0 {label} events in {city.name} right now",
                    )
                )
        units = reg.units(city=city.slug)
        healthy = sum(1 for u in units if load_health(db, u.key).state in ("healthy", "recovering"))
        if healthy < 3:
            out.append(
                (
                    f"Widen {city.name} coverage (only {healthy} healthy sources)",
                    "cities",
                    4,
                    3,
                    "auto: thin coverage makes the city feel empty",
                )
            )
        if events:
            no_geo = sum(1 for e in events if e["location"].get("lat") is None)
            if no_geo / len(events) > 0.3:
                out.append(
                    (
                        f"Improve geocoding for {city.name} ({no_geo}/{len(events)} events unmapped)",
                        "data-quality",
                        3,
                        2,
                        "auto: map view and distance filters miss these",
                    )
                )
            if not any((e.get("registration") or {}).get("closes_at") for e in events):
                out.append(
                    (
                        f"Find registration deadlines for {city.name}",
                        "sources",
                        4,
                        2,
                        "auto: the Deadlines view is empty — the core promise",
                    )
                )
        for u in units:
            h = load_health(db, u.key)
            if h.state == "quarantined":
                out.append(
                    (
                        f"Fix quarantined unit {u.key}",
                        "health",
                        5,
                        2,
                        f"auto: {h.last_error_kind}: {(h.last_error or '')[:80]}",
                    )
                )
    return out


def main() -> int:
    db = Database(Settings().db_path)
    data = ledger.load()
    added = []
    for title, area, v, e, why in propose(db):
        try:
            idea = ledger.add(data, title, area, v, e, why, confidence=0.7, source="auto")
            added.append(idea)
        except ValueError:
            continue  # already in the ledger
    ledger.save(data)
    ledger.IDEAS_MD.write_text(ledger.render(data) + "\n")
    for i in added:
        print(f"{i['id']} {i['title']}")
    print(f"{len(added)} new auto-ideas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
