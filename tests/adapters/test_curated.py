"""Curated registry + page-watch. Pages are synthetic strings here (the real registry is checked live)."""

from datetime import UTC, datetime

import pytest
import yaml
from pydantic import ValidationError

from gotc.adapters.base import FetchContext, get_adapter
from gotc.adapters.curated import CuratedEntry, evidence_present
from gotc.pipeline.ingest import parse_payloads
from gotc.settings import CONFIG_DIR, Settings
from tests.conftest import FixtureTransport, fast_client, make_city, make_source, unit_for

NOW = datetime(2026, 10, 16, 15, tzinfo=UTC)  # Fri 10am Chicago

ENTRIES = [
    {
        "id": "league",
        "title": "Curling League",
        "category": "sports_league.curling",
        "kind": "season",
        "start": "2026-11-16",
        "at": "16:00",
        "price_min": 50,
        "price_max": 50,
        "registration": {"closes": "2026-11-01", "status": "open", "signup_types": ["individual"]},
        "evidence": "sessions starting Nov 16 ... $50 + tax",
        "source_url": "https://club.example/",
        "verified_at": "2026-10-01",
    },
    {
        "id": "run",
        "title": "Tuesday Run Club",
        "category": "fitness.run_club",
        "free": True,
        "weekly": {"days": ["TU"], "at": "18:00", "occurrences": 3},
        "evidence": "Every Tuesday at 6PM",
        "source_url": "https://runs.example/",
        "verified_at": "2026-10-01",
    },
]


def run_parse(tmp_path, pages: dict[str, tuple[int, str]]):
    reg = tmp_path / "reg.yaml"
    reg.write_text(yaml.safe_dump(ENTRIES))
    src = make_source("curated_t", "curated", path=str(reg))
    unit = unit_for(src, make_city("testville", [src]))
    t = FixtureTransport()
    for url, (status, body) in pages.items():
        t.add(url.replace(".", r"\.") + "$", body, status=status)
    ctx = FetchContext(unit=unit, http=fast_client(t), now=NOW, settings=Settings())
    fr = get_adapter("curated").fetch(ctx)
    parsed = parse_payloads(get_adapter("curated"), unit, [(p, None) for p in fr.payloads], NOW)
    assert not parsed.rejects, parsed.rejects
    return {ev.record_id: ev for ev, _ in parsed.valid}


def test_evidence_check_handles_elisions_markup_and_quotes():
    page = "<p>Two sessions starting   Nov 16 and Jan 25.</p><b>$50&nbsp;+ tax</b> it’s"
    assert evidence_present("sessions starting Nov 16 ... $50 + tax", page)
    assert not evidence_present("sessions starting Dec 1 ... $50 + tax", page)


def test_reverified_when_quote_still_on_page(tmp_path):
    evs = run_parse(
        tmp_path,
        {
            "https://club.example/": (200, "Sessions starting Nov 16 and Jan 25. $50 + tax"),
            "https://runs.example/": (200, "Every Tuesday at 6PM"),
        },
    )
    league = evs["league"]
    assert league.extras["page_watch"] == "evidence_present"
    assert league.fetched_at == NOW  # re-verified today
    assert league.start.isoformat() == "2026-11-16T16:00:00-06:00"
    assert league.registration and league.registration.closes_at.hour == 23
    assert league.registration.method == "curated"
    runs = sorted(k for k in evs if k.startswith("run:"))
    assert runs == ["run:2026-10-20", "run:2026-10-27", "run:2026-11-03"]  # stable, date-based ids
    assert evs["run:2026-10-20"].price.is_free


def test_page_changed_flags_and_freezes_freshness(tmp_path):
    evs = run_parse(
        tmp_path,
        {
            "https://club.example/": (200, "Leagues are full for 2026-27"),
            "https://runs.example/": (200, "Every Tuesday at 6PM"),
        },
    )
    league = evs["league"]
    assert league.extras["page_watch"] == "page_changed"
    assert league.fetched_at < NOW  # freshness stops at verified_at → goes stale on schedule
    assert "page changed" in (league.description or "")
    assert league.registration and league.registration.confidence < 0.9


def test_blocked_page_is_unchecked_not_a_failure(tmp_path):
    evs = run_parse(
        tmp_path, {"https://club.example/": (403, "no"), "https://runs.example/": (200, "Every Tuesday at 6PM")}
    )
    assert evs["league"].extras["page_watch"] == "unchecked"


def test_entries_require_evidence_and_verification():
    with pytest.raises(ValidationError):
        CuratedEntry.model_validate({k: v for k, v in ENTRIES[0].items() if k != "evidence"})
    with pytest.raises(ValidationError):
        CuratedEntry.model_validate({**ENTRIES[0], "made_up_field": 1})


@pytest.mark.parametrize("path", sorted((CONFIG_DIR / "registry").glob("*.yaml")), ids=lambda p: p.stem)
def test_real_registries_validate(path):
    from gotc.taxonomy import taxonomy

    for raw in yaml.safe_load(path.read_text()):
        e = CuratedEntry.model_validate(raw)
        assert taxonomy().is_valid(e.category), e.category
