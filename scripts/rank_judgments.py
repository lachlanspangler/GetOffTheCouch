"""Build a judgments file from a hand-written label sheet (RANKING.md §3.1).

    .venv/bin/python scripts/rank_judgments.py <city> <labels.txt> [--merge]

Each sheet line is `<event_id> <grades> <rationale>`: one 0–3 digit per persona, in PERSONAS order. Grades are
human/agent judgments made by reading the event (title, venue, time, price, description), never by looking at a
ranker's order. The script only adds the title and fingerprint from the frozen snapshot so labels survive id churn.
With --merge, existing labels are kept and new ids are added (incremental labeling after re-pooling).
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "web" / "tests" / "rank" / "fixtures"
PERSONAS = ["newcomer_default", "social_25", "active_30", "culture_free", "parent_35", "nerd_40"]
RULES = [
    {
        "when": {"tags_any": ["kids_teens"]},
        "except_persona": ["parent_35"],
        "grade": 0,
        "why": "kids content for adults",
    },
    {"when": {"flags_any": ["hard_noise", "admin"]}, "grade": 0, "why": "administrative noise or cancelled"},
]


def main(city: str, sheet: Path, merge: bool) -> None:
    snap = json.loads(gzip.open(FIX / f"{city}.feed.json.gz").read())
    by_id = {e["id"]: e for e in snap["events"]}
    out_path = FIX / f"{city}.judgments.json"
    labels: dict[str, dict[str, str]] = {}
    if merge and out_path.exists():
        labels = json.loads(out_path.read_text())["labels"]
    for line in sheet.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        eid, grades, why = line.split(" ", 2)
        if len(grades) != len(PERSONAS) or not set(grades) <= set("0123"):
            raise SystemExit(f"bad grades for {eid}: {grades}")
        e = by_id.get(eid)
        if e is None:
            raise SystemExit(f"{eid} is not in the {city} snapshot")
        labels[eid] = {"g": grades, "fp": (e.get("rank") or {}).get("fp", ""), "t": e["title"][:80], "why": why}
    doc = {
        "version": 1,
        "city": city,
        "snapshot": f"{city}.feed.json.gz",
        "now": snap["now"],
        "labeler": "agent:claude (read each event; no human spot-check yet)",
        "personas": PERSONAS,
        "labels": dict(sorted(labels.items())),
        "rules": RULES,
    }
    out_path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"{city}: {len(labels)} labels → {out_path.name}")


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]), "--merge" in sys.argv)
