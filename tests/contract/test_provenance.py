"""Honest provenance (ADR-0006, ADR-0010): nothing that came from our config is ever labelled "reported by the
source", and no published event carries a category it can't stand behind.

Runs on (1) a fresh build from synthetic records whose sources fill fields from config, and (2) every real export in
web/public/data (the self-healing loop runs tests/contract after each run, so CI checks the live data too).
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest

from gotc.config import load_registry
from gotc.pipeline.build import build_city
from gotc.pipeline.export import city_feed
from gotc.schema import SourceEvent
from gotc.settings import ROOT
from gotc.storage.db import iso
from gotc.taxonomy import FALLBACK, taxonomy
from tests.conftest import NOW, make_city, make_registry, make_source

TAX = taxonomy()
LABEL_NOTES = ("source label", "the source's own event type")


def check_event(ev: dict, prov: dict, params_by_source: dict[str, dict]) -> list[str]:
    """Problems with one exported event's provenance (empty = honest)."""
    out: list[str] = []
    cat = ev["category"]
    if not TAX.is_valid(cat):
        out.append(f"{ev['id']}: category {cat!r} is not a taxonomy id")
    p = prov.get("category")
    if p is None:
        out.append(f"{ev['id']}: no category provenance")
        return out
    params = params_by_source.get(p["source"], {})
    if p["method"] == "reported":
        note = p.get("note") or ""
        if not note.startswith(LABEL_NOTES):
            out.append(f"{ev['id']}: category 'reported' without a source label ({note!r})")
        if cat == params.get("default_category") and not note.startswith(LABEL_NOTES):
            out.append(f"{ev['id']}: config default {cat!r} labelled reported")
    if cat == FALLBACK:
        if p["method"] != "defaulted":
            out.append(f"{ev['id']}: uncategorized but category method is {p['method']!r}")
        if ev.get("social") is not None:
            out.append(f"{ev['id']}: uncategorized listing has a meeting-people score")
        att = ev.get("attendance")
        if att and "category prior" in (att.get("method") or ""):
            out.append(f"{ev['id']}: uncategorized listing has a category-prior crowd estimate")
    org = prov.get("organizer")
    if org and org["method"] == "reported":
        configured = params_by_source.get(org["source"], {}).get("organizer")
        if configured and ev.get("organizer") == configured:
            out.append(f"{ev['id']}: config organizer {configured!r} labelled reported")
    loc = prov.get("location")
    if loc and loc["method"] == "reported":
        sp = params_by_source.get(loc["source"], {})
        configured = {sp.get("venue_label"), sp.get("venue_name"), (sp.get("venue") or {}).get("name")} - {None}
        if (ev.get("location") or {}).get("venue_name") in configured and loc["source"] == ev["sources"][0][
            "source_id"
        ]:
            out.append(f"{ev['id']}: config venue labelled reported")
    return out


# ── (1) a fresh build where config fills the category, organizer and venue ──
SRC = make_source(
    "bar_calendar",
    adapter="tribe",
    default_category="nightlife.comedy",
    single_kind_reason="a comedy club's calendar",
    organizer="The Laugh Room",
    venue_label="The Laugh Room",
)
CITY = make_city("testville", [SRC])
REG = make_registry(CITY)


def put(db, title: str, **kw) -> None:
    ev = SourceEvent.model_validate(
        {
            "source_id": SRC.id,
            "record_id": title,
            "city": CITY.slug,
            "title": title,
            "start": NOW + timedelta(days=2),
            "timezone": CITY.timezone,
            "fetched_at": NOW,
            **kw,
        }
    )
    db.execute(
        "INSERT INTO source_records (source_id, record_id, city, unit, data, content_hash, start_at, first_seen,"
        " last_seen) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            SRC.id,
            title,
            CITY.slug,
            f"{SRC.id}@testville",
            ev.model_dump_json(),
            title,
            iso(ev.start),
            iso(NOW),
            iso(NOW),
        ),
    )


def test_config_filled_fields_are_never_labelled_reported(db):
    # legacy records (no category_basis): the build must work it out from the config, not trust it
    put(db, "Open Mic Night", category="nightlife.comedy", organizer="The Laugh Room",
        location={"venue_name": "The Laugh Room"})  # fmt: skip
    put(db, "Mystery listing", category=FALLBACK)
    put(db, "Pub trivia", category="trivia_games.trivia", organizer="Quizmasters LLC",
        source_categories=["Trivia"])  # fmt: skip
    build_city(db, REG, CITY, NOW, geocoder=None)
    feed = city_feed(db, REG, CITY, NOW)
    by_title = {e.title: e for e in feed.events}
    provs = {e.id: e.provenance for e in feed.events}
    mic = provs[by_title["Open Mic Night"].id]
    assert mic["category"].method == "defaulted" and "config" in (mic["category"].note or "")
    assert mic["organizer"].method == "defaulted" and mic["location"].method == "defaulted"
    mystery = by_title["Mystery listing"]
    assert provs[mystery.id]["category"].method == "defaulted"
    assert mystery.attendance is None and mystery.social is None
    trivia = provs[by_title["Pub trivia"].id]
    assert trivia["category"].method in ("derived", "reported") and trivia["organizer"].method == "reported"
    params = {SRC.id: SRC.params}
    for e in feed.events:
        assert check_event(json.loads(e.model_dump_json()), json.loads(_dump(provs[e.id])), params) == []


def _dump(prov: dict) -> str:
    return json.dumps({k: json.loads(v.model_dump_json()) for k, v in prov.items()})


def test_the_checker_catches_the_fiu_bug():
    ev = {"id": "e1", "category": "learning.networking", "sources": [{"source_id": "fiu_events"}],
          "social": {"score": 0.6}, "attendance": None}  # fmt: skip
    prov = {"category": {"source": "fiu_events", "method": "reported", "note": None}}
    problems = check_event(ev, prov, {"fiu_events": {"default_category": "learning.networking"}})
    assert any("labelled reported" in p for p in problems)


# ── (2) every real export ──
DATA = ROOT / "web" / "public" / "data" / "cities"
EXPORTS = sorted(p for p in DATA.glob("*.json") if ".details" not in p.name)


@pytest.mark.parametrize("path", EXPORTS, ids=[p.stem for p in EXPORTS])
def test_real_exports_have_honest_provenance(path: Path):
    feed = json.loads(path.read_text())
    details_path = path.with_name(path.stem + ".details.json")
    details = json.loads(details_path.read_text())["events"] if details_path.exists() else {}
    params = {sid: s.params for sid, s in load_registry().all_sources().items()}
    problems: list[str] = []
    for ev in feed["events"]:
        prov = (details.get(ev["id"]) or {}).get("provenance") or ev.get("provenance") or {}
        problems += check_event(ev, prov, params)
    assert not problems, "\n".join(problems[:30])
