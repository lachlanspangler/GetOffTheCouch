"""Ideas ledger: docs/ideas_ledger.json is the single source of truth; docs/IDEAS.md is generated from it.

(GameCred kept a hand-edited IDEAS.md *and* a JSON ledger, and they drifted. Here the JSON is canonical and
the Markdown is a view, so there is nothing to keep in sync by hand.)

    python -m gotc.ideas add "Weather badge on outdoor events" --area ux --value 4 --effort 2 --why "..."
    python -m gotc.ideas set I-012 done --note "shipped in 3f2a1c"
    python -m gotc.ideas reject I-019 --why "Meetup API needs Pro ($$$)"
    python -m gotc.ideas next          # top open ideas by score
    python -m gotc.ideas render        # rewrite docs/IDEAS.md

Score = value × confidence ÷ effort (value/effort 1–5, confidence 0.5–1.0). Ties → lower effort first.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gotc.settings import DOCS_DIR

LEDGER = DOCS_DIR / "ideas_ledger.json"
IDEAS_MD = DOCS_DIR / "IDEAS.md"
STATUSES = ("open", "doing", "done", "rejected", "parked", "blocked")
AREAS = ("pipeline", "sources", "cities", "data-quality", "health", "ux", "features", "infra", "growth")


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def load(path: Path = LEDGER) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "ideas": []}
    data: dict[str, Any] = json.loads(path.read_text())
    return data


def save(data: dict[str, Any], path: Path = LEDGER) -> None:
    data["ideas"].sort(key=lambda i: int(i["id"].split("-")[1]))
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def score(i: dict[str, Any]) -> float:
    return round(float(i["value"]) * float(i.get("confidence", 0.8)) / max(1, int(i["effort"])), 2)


def next_id(data: dict[str, Any]) -> str:
    n = max((int(i["id"].split("-")[1]) for i in data["ideas"]), default=0)
    return f"I-{n + 1:03d}"


def add(
    data: dict[str, Any],
    title: str,
    area: str,
    value: int,
    effort: int,
    why: str,
    confidence: float = 0.8,
    status: str = "open",
    source: str = "agent",
) -> dict[str, Any]:
    if area not in AREAS:
        raise ValueError(f"area must be one of {AREAS}")
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    if any(i["title"].lower() == title.lower() for i in data["ideas"]):
        raise ValueError(f"duplicate idea: {title}")
    idea = {
        "id": next_id(data),
        "title": title,
        "area": area,
        "value": value,
        "effort": effort,
        "confidence": confidence,
        "status": status,
        "why": why,
        "source": source,
        "created": _today(),
        "updated": _today(),
        "notes": [],
    }
    data["ideas"].append(idea)
    return idea


def set_status(data: dict[str, Any], iid: str, status: str, note: str | None = None) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    idea: dict[str, Any] = next(i for i in data["ideas"] if i["id"] == iid)
    idea["status"] = status
    idea["updated"] = _today()
    if note:
        idea["notes"].append(f"{_today()} {status}: {note}")
    return idea


def render(data: dict[str, Any]) -> str:
    ideas = data["ideas"]
    out = [
        "# Ideas",
        "",
        "_Generated from `docs/ideas_ledger.json` by `python -m gotc.ideas render`. Edit the ledger via the CLI, not this file._",
        "",
        "Score = value × confidence ÷ effort. The loop (docs/WORKFLOW.md) always picks the top **open** idea,",
        "unless docs/HEALTH.md has something red.",
        "",
    ]
    counts = {s: sum(1 for i in ideas if i["status"] == s) for s in STATUSES}
    out.append(" · ".join(f"**{s}** {n}" for s, n in counts.items() if n))
    out.append("")
    for title, statuses in (
        ("Up next (open, by score)", ("doing", "open")),
        ("Blocked (needs something only a human can provide)", ("blocked",)),
        ("Parked", ("parked",)),
        ("Done", ("done",)),
        ("Rejected (and why)", ("rejected",)),
    ):
        rows = [i for i in ideas if i["status"] in statuses]
        if not rows:
            continue
        if statuses[0] in ("doing", "open"):
            rows.sort(key=lambda i: (i["status"] != "doing", -score(i), i["effort"]))
        else:
            rows.sort(key=lambda i: i["id"], reverse=True)
        out += [
            f"## {title}",
            "",
            "| ID | Idea | Area | V | E | Score | Status | Why / notes |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for i in rows:
            note = i["why"] + (f" — {i['notes'][-1]}" if i["notes"] else "")
            out.append(
                f"| {i['id']} | {i['title']} | {i['area']} | {i['value']} | {i['effort']} | {score(i)} | "
                f"{i['status']} | {note.replace('|', '/')} |"
            )
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m gotc.ideas")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("title")
    a.add_argument("--area", required=True, choices=AREAS)
    a.add_argument("--value", type=int, required=True, choices=range(1, 6))
    a.add_argument("--effort", type=int, required=True, choices=range(1, 6))
    a.add_argument("--confidence", type=float, default=0.8)
    a.add_argument("--why", required=True)
    a.add_argument("--status", default="open", choices=STATUSES)
    s = sub.add_parser("set")
    s.add_argument("id")
    s.add_argument("status", choices=STATUSES)
    s.add_argument("--note")
    r = sub.add_parser("reject")
    r.add_argument("id")
    r.add_argument("--why", required=True)
    n = sub.add_parser("next")
    n.add_argument("-n", type=int, default=10)
    sub.add_parser("render")
    args = p.parse_args(argv)
    data = load()
    if args.cmd == "add":
        idea = add(data, args.title, args.area, args.value, args.effort, args.why, args.confidence, args.status)
        print(f"{idea['id']} added (score {score(idea)})")
    elif args.cmd == "set":
        set_status(data, args.id, args.status, args.note)
    elif args.cmd == "reject":
        set_status(data, args.id, "rejected", args.why)
    elif args.cmd == "next":
        rows = sorted(
            (i for i in data["ideas"] if i["status"] in ("open", "doing")),
            key=lambda i: (-score(i), i["effort"]),
        )
        for i in rows[: args.n]:
            print(f"{i['id']}  {score(i):>4}  [{i['area']}] {i['title']}")
        return 0
    save(data)
    IDEAS_MD.write_text(render(data) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
