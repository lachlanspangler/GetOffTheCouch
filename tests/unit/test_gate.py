"""Go-live gate (SCALING.md §3, ADR-0008): criteria, pillars, tier hysteresis, export + persistence."""

import json
from datetime import timedelta

from gotc.pipeline.gate import GateInputs, RunHistory, decide_tier, evaluate, gate_city
from gotc.schema import Event, EventKind, Location, Method, Price, Registration, SourceRef, SourceStatus
from tests.conftest import NOW, make_city, make_registry

FAMILIES = ["socrata", "tribe", "bibliocommons", "localist", "ics", "volo", "trumba", "curated"]
# a healthy, balanced city: 8 sources over 8 families, ~360 events over the next 30 days
CATS = [
    "music.concert",
    "trivia_games.trivia",
    "volunteer.one_off",
    "outdoors.park",
    "fitness.run_club",
    "arts.museum",
    "community.market",
    "food_drink.tasting",
    "family.kids",
    "learning.tech",
    "nightlife.comedy",
    "sports_watch.game",
]


def _ev(i: int, cat: str, src: str, *, lat: float | None = 44.97, days: float = 1.0, **kw) -> Event:
    start = NOW + timedelta(days=days, hours=i % 7)
    return Event(
        id=f"evt_{i}",
        city="testville",
        title=kw.pop("title", f"Event {i}"),
        kind=kw.pop("kind", EventKind.ONE_OFF),
        category=cat,
        start=start,
        timezone="America/Chicago",
        location=Location(lat=lat, lon=-93.26 if lat is not None else None),
        price=Price(),
        sources=[SourceRef(source_id=src, record_id=str(i), fetched_at=NOW)],
        first_seen=NOW,
        last_checked=NOW,
        **kw,
    )


def healthy_events() -> list[Event]:
    evs = []
    for i in range(360):
        cat = CATS[i % len(CATS)]
        evs.append(_ev(i, cat, f"src{i % 8}", days=(i % 13) + 0.5))
    evs.append(_ev(900, "sports_league.kickball", "src7", days=40))
    for j in range(12):  # published deadlines
        evs.append(
            _ev(
                1000 + j,
                "sports_league.softball",
                "src7",
                days=50,
                registration=Registration(closes_at=NOW + timedelta(days=20), method=Method.REPORTED),
            )
        )
    return evs


def statuses(n: int = 8, state: str = "healthy") -> list[SourceStatus]:
    return [
        SourceStatus(
            source_id=f"src{i}",
            name=f"S{i}",
            state=state,  # type: ignore[arg-type]
            last_success_at=NOW - timedelta(hours=2),
            sla_hours=24,
            stale=False,
            records=50,
        )
        for i in range(n)
    ]


def inputs(events=None, sts=None, runs=None, **kw) -> GateInputs:
    hist = RunHistory(
        runs=runs if runs is not None else [(NOW - timedelta(hours=h), 8, 0) for h in range(0, 72, 6)],
        valid=1000,
        rejected=5,
    )
    return GateInputs(
        city=make_city(),
        now=NOW,
        events=healthy_events() if events is None else events,
        statuses=statuses() if sts is None else sts,
        adapters={f"src{i}": FAMILIES[i] for i in range(8)},
        homepages={},
        cadence_hours=dict.fromkeys((f"src{i}" for i in range(8)), 24.0),
        history=hist,
        live_records=400,
        outside_records=2,
        **kw,
    )


def test_healthy_city_passes_every_hard_criterion():
    cov = evaluate(inputs())
    failing = {k: v for k, v in cov.criteria.items() if v.pass_hard is False}
    assert cov.passed_hard, failing
    assert cov.tier == "live"
    assert set(cov.criteria) == {f"G{i}" for i in range(1, 12)}
    assert cov.pillars["deadlines"].state == "strong" and cov.pillars["deadlines"].count == 12
    assert cov.pillars["cons_faires"].state == "none" and "cons" in (cov.pillars["cons_faires"].note or "")
    assert cov.geocode_rate == 1.0 and cov.sources_healthy == 8


def test_thin_sources_and_one_dominant_source_fail_hard():
    evs = [_ev(i, "arts.books", "src0", days=1 + i % 10) for i in range(300)]
    cov = evaluate(inputs(events=evs, sts=statuses(5)))
    assert not cov.passed_hard
    for cid in ("G1", "G3", "G4", "G5", "G6", "G7"):
        assert cov.criteria[cid].pass_hard is False, cid
    assert cov.top_source == "src0" and cov.top_source_share == 1.0
    assert any(r.startswith("G7") and "src0" in r for r in cov.reasons)


def test_geocode_bar_is_hard_at_80_soft_at_90():
    evs = healthy_events()
    for e in evs[:60]:  # 60 / 373 ≈ 16% unmapped → 84%: passes hard, fails soft
        e.location = Location()
    cov = evaluate(inputs(events=evs))
    g8 = cov.criteria["G8"]
    assert g8.pass_hard is True and g8.pass_soft is False
    assert any(r.startswith("thin: G8") for r in cov.reasons)


def test_small_metro_has_lower_g2_bar():
    evs = healthy_events()[:200]
    assert evaluate(inputs(events=evs)).criteria["G2"].pass_hard is False
    assert evaluate(inputs(events=evs, msa_pop_m=1.2)).criteria["G2"].pass_hard is True


def test_stability_needs_three_green_runs_over_48h():
    short = [(NOW - timedelta(hours=h), 8, 0) for h in range(0, 12, 3)]
    assert evaluate(inputs(runs=short)).criteria["G10"].pass_hard is False
    broken = [(NOW, 8, 0), (NOW - timedelta(hours=1), 8, 4), *[(NOW - timedelta(hours=h), 8, 0) for h in (10, 60)]]
    assert evaluate(inputs(runs=broken)).criteria["G10"].pass_hard is False
    one_flaky = [(NOW - timedelta(hours=h), 12, 1) for h in range(0, 72, 6)]
    assert evaluate(inputs(runs=one_flaky)).criteria["G10"].pass_hard is True


def test_weekly_units_are_not_overdue_between_runs():
    sts = statuses()
    sts[0].last_success_at = NOW - timedelta(days=5)
    gi = inputs(sts=sts)
    gi.cadence_hours["src0"] = 168
    assert evaluate(gi).criteria["G9"].pass_hard is True
    gi.cadence_hours["src0"] = 24
    assert evaluate(gi).criteria["G9"].pass_hard is False


def test_duplicates_count_one_card_per_series_per_day():
    evs = healthy_events()
    dup = [_ev(5000 + i, "music.concert", "src1", days=2, title="Same Show") for i in range(30)]
    assert evaluate(inputs(events=evs + dup)).criteria["G11"].pass_soft is False
    for e in dup:
        e.series_id = "ser_x"
    assert evaluate(inputs(events=evs + dup)).criteria["G11"].pass_soft is True


def test_tier_hysteresis():
    good = evaluate(inputs())
    bad = evaluate(inputs(sts=statuses(3)))
    # new city: beta until it passes, then live immediately
    assert decide_tier(bad, True, None, None, False, NOW)[0] == "beta"
    assert decide_tier(good, True, "beta", NOW - timedelta(days=1), False, NOW) == ("live", None, False)
    # incumbent / live city: banner after 72 h, demoted after 7 days
    assert decide_tier(bad, True, None, None, True, NOW) == ("live", NOW, False)
    t, _since, banner = decide_tier(bad, True, "live", NOW - timedelta(hours=80), False, NOW)
    assert (t, banner) == ("live", True)
    assert decide_tier(bad, True, "live", NOW - timedelta(days=8), False, NOW)[0] == "beta"
    # disabled = hidden, whatever the numbers say
    assert decide_tier(good, False, "live", None, True, NOW)[0] == "hidden"


def test_gate_city_persists_and_logs_transitions(db):
    city = make_city()
    reg = make_registry(city)
    cov = gate_city(db, reg, city, NOW, healthy_events())
    assert cov.tier == "beta"  # no healthy units in this DB, and testville isn't an incumbent metro
    row = db.one("SELECT * FROM city_gate WHERE city = 'testville'")
    assert row["tier"] == "beta" and json.loads(row["data"])["tier"] == "beta"
    gate_city(db, reg, city, NOW + timedelta(hours=1), healthy_events())
    logs = db.all("SELECT * FROM health_log WHERE unit = 'gate@testville'")
    assert len(logs) == 1 and "new → beta" in logs[0]["message"]  # logged once, on the transition only


def test_disabled_city_is_hidden_and_not_exported(db, settings):
    from gotc.pipeline.export import export_all

    live = make_city()
    draft = make_city("draftville").model_copy(update={"enabled": False})
    index = export_all(db, make_registry(live, draft), settings.web_data_dir, NOW)
    assert [c["slug"] for c in index["cities"]] == ["testville"]
    assert index["cities"][0]["tier"] == "beta"
    assert not (settings.web_data_dir / "cities" / "draftville.json").exists()
