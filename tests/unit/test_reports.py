"""'Report a problem' issues → gate examples (I-224)."""

from __future__ import annotations

from pathlib import Path

import yaml

from gotc import reports

FORM = {
    "number": 41,
    "url": "https://github.com/lachlanspangler/GetOffTheCouch/issues/41",
    "createdAt": "2026-11-02T18:00:00Z",
    "title": "Data report: Fall B: Last day to withdraw from the University with a 25% refund of tuition",
    "body": (
        "### What's wrong?\n\nNot a real event (nobody can go: a deadline, closure, office hours, internal meeting…)\n\n"
        "### Listing\n\nFall B: Last day to withdraw from the University with a 25% refund of tuition\n\n"
        "### Event id\n\nevt_abc123\n\n### City\n\nmiami\n\n### Link\n\nhttps://x/miami/events/fall-b\n\n"
        "### Sources\n\nfiu_events https://calendar.fiu.edu/event/1\n\n### Details\n\nIt's a tuition deadline\n"
    ),
}
LEGACY = {
    "number": 7,
    "title": "Data report: Closed for Private Event",
    "body": "Event: Closed for Private Event\nLink: https://x\nID: evt_9\nCity: nyc\nSources: zinc_bar https://z\n\nWhat's wrong?\nnot a real event\n",
}


def test_parse_issue_form_and_legacy_bodies():
    r = reports.parse_issue(FORM)
    assert (r.number, r.problem, r.event_id, r.city, r.sources) == (
        41,
        "not_event",
        "evt_abc123",
        "miami",
        ["fiu_events"],
    )
    assert r.listing.startswith("Fall B: Last day to withdraw")
    old = reports.parse_issue(LEGACY)
    assert (old.problem, old.event_id, old.city, old.sources) == ("not_event", "evt_9", "nyc", ["zinc_bar"])


def test_import_suggests_a_rule_and_is_idempotent_then_promote_adds_a_golden_example(tmp_path: Path):
    pending, golden = tmp_path / "reports.yaml", tmp_path / "golden.yaml"
    other = {
        **LEGACY,
        "number": 8,
        "title": "Data report: Weird listing",
        "body": LEGACY["body"].replace("Closed for Private Event", "Weird listing"),
    }
    added = reports.import_reports([FORM, other], db=None, path=pending)
    assert [a["issue"] for a in added] == [8, 41]
    entry = next(a for a in added if a["issue"] == 41)
    rule = entry["suggested_override"]["listing_gate"]["reject"][0]
    assert rule["id"] == "report_41" and "withdraw" in rule["pattern"] and "#41" in rule["reason"]
    assert reports.import_reports([FORM], db=None, path=pending) == []  # already imported
    reports.promote(41, "not_event", path=pending, golden=golden)
    [g] = yaml.safe_load(golden.read_text())
    assert g["label"] == "not_event" and g["origin"] == "report#41" and g["source_id"] == "fiu_events"
    assert next(e for e in yaml.safe_load(pending.read_text()) if e["issue"] == 41)["status"] == "reviewed"


def test_suggested_patterns_compile_and_match_the_reported_title():
    import re

    for title in ["Fall B: Last day to withdraw from the University with a 25% refund of tuition", "Closed (Nov 26)"]:
        assert re.search(reports.suggest_pattern(title), title.lower())
