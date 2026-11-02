"""Turn "Report a problem" issues into gate examples and candidate rules (ADR-0010, I-224).

    gh issue list -R lachlanspangler/GetOffTheCouch --label data-report --state all \\
        --json number,title,body,url,createdAt --limit 500 > reports.json
    gotc reports import reports.json          # → config/listing_gate_reports.yaml (pending review)
    gotc reports promote 123 --label not_event # → tests/fixtures/listing_gate/golden.yaml (+ status: reviewed)

``import`` parses each issue (the issue form's fields, or the older free-text body), finds the listing's source
records, re-runs the gate on them, and records a suggested per-source rule. Nothing changes the gate by itself:
a person reviews the pending file, generalizes good suggestions into ``config/listing_gate.yaml`` and promotes
the example into the golden set, so the precision/recall test guards the new rule from then on.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from gotc.settings import CONFIG_DIR, ROOT

REPORTS_FILE = CONFIG_DIR / "listing_gate_reports.yaml"
GOLDEN_FILE = ROOT / "tests" / "fixtures" / "listing_gate" / "golden.yaml"

PROBLEMS = {
    "not a real event": "not_event",
    "wrong category": "wrong_category",
    "wrong date": "wrong_time",
    "wrong place": "wrong_place",
    "duplicate": "duplicate",
    "cancelled": "cancelled",
}
_FORM_FIELD = re.compile(r"^###\s+(.+?)\s*$", re.M)
_LEGACY = {"event": "listing", "id": "event_id", "city": "city", "link": "link", "sources": "sources"}


@dataclass
class Report:
    number: int
    url: str
    reported_at: str
    problem: str  # not_event | wrong_category | … | other
    listing: str
    event_id: str | None
    city: str | None
    sources: list[str]
    details: str


def parse_issue(issue: dict[str, Any]) -> Report:
    """Fields from an issue-form body ("### Label\\n\\nvalue") or the older "Key: value" body."""
    body = str(issue.get("body") or "")
    fields: dict[str, str] = {}
    parts = _FORM_FIELD.split(body)
    if len(parts) > 1:
        for label, value in zip(parts[1::2], parts[2::2], strict=False):
            v = value.strip()
            fields[label.strip().lower()] = "" if v == "_No response_" else v
    else:
        for line in body.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                if k.strip().lower() in _LEGACY:
                    fields[_LEGACY[k.strip().lower()]] = v.strip()
        tail = body.split("What's wrong?", 1)
        fields["details"] = tail[1].strip() if len(tail) > 1 else ""
    problem_text = (fields.get("what's wrong?") or fields.get("details") or "").lower()
    problem = next((v for k, v in PROBLEMS.items() if k in problem_text), "other")
    listing = fields.get("listing") or re.sub(r"^Data report:\s*", "", str(issue.get("title") or ""))
    sources = [s.split()[0] for s in re.split(r",\s*", fields.get("sources", "")) if s.strip()]
    return Report(
        number=int(issue["number"]),
        url=str(issue.get("url") or ""),
        reported_at=str(issue.get("createdAt") or issue.get("created_at") or ""),
        problem=problem,
        listing=listing.strip(),
        event_id=(fields.get("event id") or fields.get("event_id") or "").strip() or None,
        city=(fields.get("city") or "").strip() or None,
        sources=sources,
        details=(fields.get("details") or "").strip()[:500],
    )


def suggest_pattern(title: str) -> str:
    """A starting regex for a reviewer to generalize: the title with numbers and dates loosened."""
    t = re.sub(r"\s+", " ", title.strip().lower())
    t = re.sub(r"^[^:]{1,20}:\s*", "", t) if len(t) > 30 else t  # drop a short "Fall B:" style prefix
    esc = re.escape(t)
    esc = re.sub(r"\d+", r"\\d+", esc)
    return rf"\b{esc[:120]}"


def load_pending(path: Path = REPORTS_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return list(yaml.safe_load(path.read_text()) or [])


def import_reports(
    issues: list[dict[str, Any]], db: Any | None = None, path: Path = REPORTS_FILE
) -> list[dict[str, Any]]:
    """Merge issues into the pending-review file. Idempotent: an issue already in the file is left as is."""
    from gotc.config import load_registry
    from gotc.pipeline.listing_gate import listing_gate
    from gotc.schema import SourceEvent

    existing = load_pending(path)
    have = {int(e["issue"]) for e in existing}
    reg = load_registry()
    sources = reg.all_sources()
    added: list[dict[str, Any]] = []
    for issue in sorted(issues, key=lambda i: int(i["number"])):
        if int(issue["number"]) in have:
            continue
        r = parse_issue(issue)
        entry: dict[str, Any] = {
            "issue": r.number,
            "url": r.url,
            "reported_at": r.reported_at,
            "problem": r.problem,
            "listing": r.listing,
            "city": r.city,
            "event_id": r.event_id,
            "sources": r.sources,
            "details": r.details,
            "status": "pending",
        }
        recs: list[SourceEvent] = []
        if db is not None and r.event_id:
            for row in db.all(
                "SELECT sr.data FROM event_members em JOIN source_records sr ON sr.source_id = em.source_id"
                " AND sr.record_id = em.record_id AND sr.city = em.city WHERE em.event_id = ?",
                (r.event_id,),
            ):
                recs.append(SourceEvent.model_validate_json(row["data"]))
        if recs:
            gate = listing_gate()
            verdicts = []
            for rec in recs:
                src = sources.get(rec.source_id)
                v = gate.evaluate(rec, src.params if src else {}, src.data_type.value if src else None)
                verdicts.append({"source_id": rec.source_id, "keep": v.keep, "rule": v.rule})
            entry["gate_now"] = verdicts
            if r.problem == "not_event" and all(not v["keep"] for v in verdicts):
                entry["status"] = "already_gated"
        if r.problem == "not_event" and entry["status"] == "pending":
            sid = r.sources[0] if r.sources else (recs[0].source_id if recs else "<source_id>")
            entry["suggested_override"] = {
                "source": sid,
                "listing_gate": {
                    "reject": [
                        {
                            "id": f"report_{r.number}",
                            "pattern": suggest_pattern(r.listing),
                            "reason": "reported as not a real event (issue #" + str(r.number) + ")",
                        }
                    ]
                },
            }
            entry["next"] = (
                "generalize the pattern into a rule in config/listing_gate.yaml (or keep it as this source's override),"
                f" then `gotc reports promote {r.number} --label not_event`"
            )
        added.append(entry)
    if added:
        path.write_text(_header() + yaml.safe_dump(existing + added, sort_keys=False, allow_unicode=True, width=110))
    return added


def promote(number: int, label: str, path: Path = REPORTS_FILE, golden: Path = GOLDEN_FILE) -> dict[str, Any]:
    """Add a reviewed report to the golden set and mark it reviewed."""
    if label not in ("event", "not_event"):
        raise ValueError("label must be event or not_event")
    pending = load_pending(path)
    entry = next((e for e in pending if int(e["issue"]) == number), None)
    if entry is None:
        raise KeyError(f"issue #{number} isn't in {path.name}; run `gotc reports import` first")
    items = list(yaml.safe_load(golden.read_text()) or []) if golden.exists() else []
    gid = f"r{number}"
    if not any(i["id"] == gid for i in items):
        items.append(
            {
                "id": gid,
                "city": entry.get("city") or "",
                "source_id": (entry.get("sources") or ["unknown"])[0],
                "title": entry["listing"],
                "label": label,
                "why": f"user report #{number}: {entry.get('details') or entry['problem']}"[:120],
                "origin": f"report#{number}",
            }
        )
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(_golden_header() + yaml.safe_dump(items, sort_keys=False, allow_unicode=True, width=110))
    entry["status"] = "reviewed"
    entry["golden_label"] = label
    path.write_text(_header() + yaml.safe_dump(pending, sort_keys=False, allow_unicode=True, width=110))
    return entry


def _header() -> str:
    return (
        "# Listing reports waiting for review (gotc reports import). Generated + hand-edited; see gotc/reports.py.\n"
        "# status: pending → review it · already_gated → the gate already holds it back · reviewed → in the golden set\n"
    )


def _golden_header() -> str:
    return (
        "# The listing gate's golden set (ADR-0010): real listings labelled event / not_event, measured on every\n"
        "# `make check` (tests/unit/test_listing_gate_golden.py). Audit labels were made blind to the rules.\n"
    )


def read_issues(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    return list(data if isinstance(data, list) else data.get("items", []))
