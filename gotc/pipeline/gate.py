"""The per-city go-live gate (docs/research/SCALING.md §3, ADR-0008) and the ``coverage`` block.

``evaluate`` is pure: exported events + source statuses + run history → G1…G11, pillars, tier inputs.
``decide_tier`` applies the publication rules with hysteresis, and ``gate_city`` persists the result in
``city_gate`` and logs every tier transition to ``health_log`` (unit ``gate@<city>``).

Tiers:
  * **live**   every hard criterion passes (soft misses become visible "thin coverage" notes)
  * **beta**   enabled, but a hard criterion fails: still exported and listed, labeled "Coming soon"
  * **hidden** ``enabled: false`` in config: never exported (drafts, discover output); ``gotc gate`` still
               evaluates it from whatever is in the DB
Hysteresis (doc §3 "Regression"): a live city failing a hard criterion keeps its tier, shows a banner after
72 h, and is demoted to beta only after 7 days. A beta city is promoted as soon as all hard criteria pass.
A city with no gate history starts as beta, except ``incumbent`` metros (published before the gate existed),
which start as live and get the same 7-day grace.

Calibration notes (deviations from the doc, each because the literal rule would block every city):
  * G9 "no enabled unit without a success in 48 h" → within max(48 h, 2 × the unit's cadence), so weekly
    units (cons, curated registries) aren't failures between their scheduled runs.
  * G10 "green run" → a run in which ≤ max(1, 10 %) of the city's attempted units failed; one flaky source
    shouldn't block a 15-source city forever. Spanning ≥ 48 h and ≥ 3 runs are as in the doc.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from gotc.config import CityConfig, Registry, Unit
from gotc.health.store import log as hlog
from gotc.metros import metros
from gotc.pipeline.textnorm import haversine_m, norm_title
from gotc.schema import (
    CityCoverage,
    CoverageCriterion,
    CoveragePillar,
    Event,
    EventKind,
    Method,
    SourceStatus,
)
from gotc.storage.db import Database, iso, parse_iso

log = logging.getLogger(__name__)

TOP_LEVEL_TOTAL = 15  # top-level taxonomy categories, excluding "other"
BANNER_AFTER = timedelta(hours=72)
DEMOTE_AFTER = timedelta(days=7)
OFFICIAL_ADAPTERS = {"socrata", "arcgis", "ckan", "csvfile", "bibliocommons", "communico", "localist", "livewhale"}
OFFICIAL_SUFFIXES = (".gov", ".edu", ".us", ".mil")

PILLARS: dict[str, tuple[str, int]] = {  # id → (label, count at which it's "strong")
    "leagues": ("Leagues", 5),
    "openings_parties": ("Openings & parties", 10),
    "concerts": ("Concerts", 20),
    "volunteering": ("Volunteering", 5),
    "cons_faires": ("Cons & faires", 2),
    "trivia": ("Trivia & games", 5),
    "deadlines": ("Deadlines", 10),
}
NONE_NOTES = {
    "leagues": "no league listings for this city yet",
    "openings_parties": "we have no license or nightlife data for this city",
    "concerts": "no concert listings yet (ticketing sources need API keys)",
    "volunteering": "no volunteer platform found for this city yet",
    "cons_faires": "no cons or faires found in the next year",
    "trivia": "no trivia or game nights found yet",
    "deadlines": "no published registration deadlines in the next 60 days",
}


@dataclass
class RunHistory:
    """Per-run outcome for one city's units: (run started_at, attempted, failed), newest first."""

    runs: list[tuple[datetime, int, int]] = field(default_factory=list)
    valid: int = 0
    rejected: int = 0


@dataclass
class GateInputs:
    city: CityConfig
    now: datetime
    events: list[Event]
    statuses: list[SourceStatus]
    adapters: dict[str, str]  # source_id → adapter
    homepages: dict[str, str | None]
    cadence_hours: dict[str, float]
    history: RunHistory
    live_records: int = 0
    outside_records: int = 0
    msa_pop_m: float | None = None
    curated_sources: set[str] = field(default_factory=set)


def _top(cat: str) -> str:
    return cat.split(".", 1)[0]


def _official(source_id: str, adapter: str, homepage: str | None) -> bool:
    if adapter in OFFICIAL_ADAPTERS:
        return True
    host = urlsplit(homepage or "").netloc.lower()
    return bool(host) and host.endswith(OFFICIAL_SUFFIXES)


def _crit(
    label: str,
    value: float | None,
    threshold: str,
    hard: bool | None = None,
    soft: bool | None = None,
    note: str | None = None,
) -> CoverageCriterion:
    return CoverageCriterion(label=label, value=value, threshold=threshold, pass_hard=hard, pass_soft=soft, note=note)


def _share(n: int, d: int) -> float:
    return round(n / d, 3) if d else 0.0


def pillars(events: list[Event], now: datetime, curated_sources: set[str]) -> dict[str, CoveragePillar]:
    in30 = [e for e in events if now - timedelta(hours=3) <= e.start <= now + timedelta(days=30)]
    upcoming = [e for e in events if (e.end or e.start) >= now - timedelta(hours=3)]
    groups: dict[str, list[Event]] = {
        # leagues and cons are planned months ahead: count everything upcoming in the export
        "leagues": [e for e in upcoming if _top(e.category) == "sports_league"],
        "openings_parties": [
            e
            for e in events
            if (e.kind == EventKind.OPENING and e.start >= now - timedelta(days=60))
            or (_top(e.category) == "nightlife" and now - timedelta(hours=3) <= e.start <= now + timedelta(days=30))
        ],
        "concerts": [e for e in in30 if _top(e.category) == "music"],
        "volunteering": [e for e in in30 if _top(e.category) == "volunteer"],
        "cons_faires": [e for e in upcoming if _top(e.category) == "niche"],
        "trivia": [e for e in in30 if _top(e.category) == "trivia_games"],
        "deadlines": [
            e
            for e in events
            if e.registration
            and e.registration.closes_at
            and now <= e.registration.closes_at <= now + timedelta(days=60)
            and e.registration.method != Method.DERIVED
        ],
    }
    out: dict[str, CoveragePillar] = {}
    for pid, (label, strong) in PILLARS.items():
        evs = groups[pid]
        n = len(evs)
        state = "none" if n == 0 else ("strong" if n >= strong else "thin")
        note = None
        if n == 0:
            note = NONE_NOTES[pid]
        elif all(s.source_id in curated_sources for e in evs for s in e.sources):
            note = "all curated"
        out[pid] = CoveragePillar(label=label, count=n, threshold=strong, state=state, note=note)
    return out


def evaluate(gi: GateInputs) -> CityCoverage:
    """All criteria + pillars for one city. ``tier`` here is provisional (live if every hard criterion passes)."""
    now, events = gi.now, gi.events
    crit: dict[str, CoverageCriterion] = {}

    # G1 healthy enabled units, families, officialness
    healthy = [s for s in gi.statuses if s.state in ("healthy", "recovering")]
    families = {gi.adapters.get(s.source_id, "?") for s in healthy}
    official = [
        s for s in healthy if _official(s.source_id, gi.adapters.get(s.source_id, ""), gi.homepages.get(s.source_id))
    ]
    g1 = len(healthy) >= 8 and len(families) >= 4 and len(official) >= 1
    crit["G1"] = _crit(
        "Healthy sources",
        len(healthy),
        "≥ 8 healthy units, ≥ 4 adapter families, ≥ 1 official",
        hard=g1,
        note=f"{len(families)} families, {len(official)} official",
    )

    # G2 events in the next 14 days (smaller bar for MSAs under 1.5 M)
    n14 = sum(1 for e in events if now - timedelta(hours=3) <= e.start <= now + timedelta(days=14))
    bar14 = 150 if gi.msa_pop_m is not None and gi.msa_pop_m < 1.5 else 250
    crit["G2"] = _crit("Events in the next 14 days", n14, f"≥ {bar14}", hard=n14 >= bar14)

    # G3 top-level categories with ≥ 3 events in the next 30 days
    in30 = [e for e in events if now - timedelta(hours=3) <= e.start <= now + timedelta(days=30)]
    tops = Counter(_top(e.category) for e in in30)
    covered = sum(1 for c, n in tops.items() if n >= 3 and c != "other")
    crit["G3"] = _crit(
        "Categories with ≥ 3 events (30 days)", covered, f"≥ 10 of {TOP_LEVEL_TOTAL}", hard=covered >= 10
    )

    # G4 newcomer pillars in the next 30 days
    upcoming = [e for e in events if (e.end or e.start) >= now - timedelta(hours=3)]
    p4 = {
        "music ≥ 20": tops.get("music", 0) >= 20,
        "trivia/games ≥ 5": tops.get("trivia_games", 0) >= 5,
        "volunteer ≥ 5": tops.get("volunteer", 0) >= 5,
        "outdoors/fitness ≥ 10": tops.get("outdoors", 0) + tops.get("fitness", 0) >= 10,
        "leagues ≥ 1": any(_top(e.category) == "sports_league" for e in upcoming),
    }
    met = sum(p4.values())
    crit["G4"] = _crit(
        "Newcomer pillars (30 days)",
        met,
        "4 of 5 (hard), 5 of 5 (soft)",
        hard=met >= 4,
        soft=met == 5,
        note="missing: " + ", ".join(k for k, v in p4.items() if not v) if met < 5 else None,
    )

    # G5 published deadlines in the next 60 days
    dl = sum(
        1
        for e in events
        if e.registration
        and e.registration.closes_at
        and now <= e.registration.closes_at <= now + timedelta(days=60)
        and e.registration.method != Method.DERIVED
    )
    crit["G5"] = _crit("Published deadlines (60 days)", dl, "≥ 1 (hard), ≥ 10 (soft)", hard=dl >= 1, soft=dl >= 10)

    # G6 category balance (all exported upcoming events)
    cat_counts = Counter(_top(e.category) for e in upcoming)
    top_cat, top_cat_n = cat_counts.most_common(1)[0] if cat_counts else (None, 0)
    cat_share = _share(top_cat_n, len(upcoming))
    crit["G6"] = _crit(
        "Largest category share",
        cat_share,
        "≤ 60% (hard), ≤ 45% (soft)",
        hard=cat_share <= 0.60,
        soft=cat_share <= 0.45,
        note=top_cat,
    )

    # G7 source balance (primary source of each upcoming event)
    src_counts = Counter(e.sources[0].source_id for e in upcoming if e.sources)
    top_src, top_src_n = src_counts.most_common(1)[0] if src_counts else (None, 0)
    src_share = _share(top_src_n, len(upcoming))
    crit["G7"] = _crit(
        "Largest single-source share",
        src_share,
        "≤ 60% (hard), ≤ 50% (soft)",
        hard=src_share <= 0.60,
        soft=src_share <= 0.50,
        note=top_src,
    )

    # G8 geocode coverage (online-only events are skipped at ingest, so every exported event counts)
    located = sum(1 for e in upcoming if e.location.lat is not None)
    geo = _share(located, len(upcoming))
    crit["G8"] = _crit("Events with coordinates", geo, "≥ 80% (hard), ≥ 90% (soft)", hard=geo >= 0.80, soft=geo >= 0.90)

    # G9 recency
    fresh = _share(sum(1 for e in upcoming if not e.stale), len(upcoming)) if upcoming else 0.0
    overdue = []
    for s in gi.statuses:
        if s.state == "disabled":
            continue
        window = timedelta(hours=max(48.0, 2 * gi.cadence_hours.get(s.source_id, 24.0)))
        if s.last_success_at is None or now - s.last_success_at > window:
            overdue.append(s.source_id)
    crit["G9"] = _crit(
        "Fresh events",
        fresh,
        "≥ 90% within SLA; every enabled unit succeeded within max(48 h, 2 × cadence)",
        hard=fresh >= 0.90 and not overdue,
        note=("no recent success: " + ", ".join(sorted(overdue)[:5])) if overdue else None,
    )

    # G10 stability
    streak: list[datetime] = []
    for at, attempted, failed in gi.history.runs:
        if failed > max(1, int(attempted * 0.10)):
            break
        streak.append(at)
    span_h = (streak[0] - streak[-1]).total_seconds() / 3600 if len(streak) >= 2 else 0.0
    total = gi.history.valid + gi.history.rejected
    reject_rate = _share(gi.history.rejected, total)
    fence = _share(gi.outside_records, gi.live_records)
    g10 = len(streak) >= 3 and span_h >= 48 and reject_rate < 0.10 and fence < 0.05
    crit["G10"] = _crit(
        "Stability",
        len(streak),
        "≥ 3 green runs over ≥ 48 h; reject rate < 10%; geofence drops < 5%",
        hard=g10,
        note=f"green streak spans {span_h:.0f} h; reject rate {reject_rate:.0%}; geofence drops {fence:.0%}",
    )

    # G11 duplicates: same normalized title on the same local day, counting one card per series
    seen: Counter[tuple[str, str]] = Counter()
    series_days: set[tuple[str, str]] = set()
    for e in upcoming:
        day = e.start.date().isoformat()
        if e.series_id:
            if (e.series_id, day) in series_days:
                continue
            series_days.add((e.series_id, day))
        seen[(norm_title(e.title), day)] += 1
    dups = sum(n - 1 for n in seen.values() if n > 1)
    dup_rate = _share(dups, sum(seen.values()))
    crit["G11"] = _crit("Duplicate rate", dup_rate, "< 3% (soft)", soft=dup_rate < 0.03)

    passed_hard = all(c.pass_hard is not False for c in crit.values())
    passed_soft = all(c.pass_soft is not False for c in crit.values())
    reasons = [
        f"{cid} {c.label}: {_fmt(cid, c.value)} (needs {c.threshold})" + (f"; {c.note}" if c.note else "")
        for cid, c in crit.items()
        if c.pass_hard is False
    ] + [
        f"thin: {cid} {c.label}: {_fmt(cid, c.value)} (soft bar {c.threshold})" + (f"; {c.note}" if c.note else "")
        for cid, c in crit.items()
        if c.pass_hard is not False and c.pass_soft is False
    ]
    pills = pillars(events, now, gi.curated_sources)
    strongest = sorted(
        (p for p in pills if pills[p].state == "strong"),
        key=lambda p: pills[p].count / pills[p].threshold,
        reverse=True,
    )[:3]
    return CityCoverage(
        tier="live" if passed_hard else "beta",
        evaluated_at=now,
        passed_hard=passed_hard,
        passed_soft=passed_soft,
        sources_healthy=len(healthy),
        sources_total=sum(1 for s in gi.statuses if s.state != "disabled"),
        pillars=pills,
        strongest=strongest,
        geocode_rate=geo,
        top_source=top_src,
        top_source_share=src_share,
        criteria=crit,
        reasons=reasons,
    )


SHARE_CRITERIA = {"G6", "G7", "G8", "G9", "G11"}


def _fmt(cid: str, v: float | None) -> str:
    if v is None:
        return "n/a"
    return f"{v:.0%}" if cid in SHARE_CRITERIA else f"{v:g}"


def decide_tier(
    computed: CityCoverage,
    enabled: bool,
    previous_tier: str | None,
    failing_since: datetime | None,
    incumbent: bool,
    now: datetime,
) -> tuple[str, datetime | None, bool]:
    """→ (tier, failing_since, banner). Pure; see the module docstring for the rules."""
    if not enabled:
        return "hidden", None, False
    prev = previous_tier or ("live" if incumbent else "beta")
    if prev == "hidden":
        prev = "beta"  # a draft that was just enabled starts in beta
    if computed.passed_hard:
        return "live", None, False
    since = failing_since or now
    if prev == "live":
        if now - since >= DEMOTE_AFTER:
            return "beta", since, False
        return "live", since, now - since >= BANNER_AFTER
    return "beta", since, False


def gather(db: Database, reg: Registry, city: CityConfig, now: datetime, events: list[Event]) -> GateInputs:
    from gotc.pipeline.export import source_statuses

    if city.enabled:
        units = reg.units(city=city.slug)
    else:  # reg.units() skips disabled cities; evaluate their configured units anyway
        units = [Unit(source=s, city=city) for s in [*reg.sources_file.sources, *city.sources]]
    statuses = source_statuses(db, reg, city, now) if city.enabled else []
    hist = RunHistory()
    rows = db.all(
        "SELECT r.id, r.started_at, COUNT(*) attempted, SUM(ru.status = 'failed') failed,"
        " SUM(ru.valid) valid, SUM(ru.rejected) rejected FROM run_units ru JOIN runs r ON r.id = ru.run_id"
        " WHERE ru.unit LIKE ? AND ru.status IN ('ok', 'failed') GROUP BY r.id ORDER BY r.started_at DESC LIMIT 400",
        (f"%@{city.slug}",),
    )
    week = now - timedelta(days=7)
    for r in rows:
        at = parse_iso(r["started_at"])
        if at is None:
            continue
        hist.runs.append((at, int(r["attempted"]), int(r["failed"] or 0)))
        if at >= week:
            hist.valid += int(r["valid"] or 0)
            hist.rejected += int(r["rejected"] or 0)
    live = db.all(
        "SELECT data FROM source_records WHERE city = ? AND gone_at IS NULL AND start_at >= ?",
        (city.slug, iso(now - timedelta(days=1))),
    )
    fence = city.radius_km * 1000 * 2.5
    outside = 0
    for r in live:
        loc = json.loads(r["data"]).get("location") or {}
        has_point = loc.get("lat") is not None and loc.get("lon") is not None
        if has_point and haversine_m(float(loc["lat"]), float(loc["lon"]), *city.center) > fence:
            outside += 1
    m = metros().get(city.slug)
    return GateInputs(
        city=city,
        now=now,
        events=events,
        statuses=statuses,
        adapters={u.source.id: u.source.adapter for u in units},
        homepages={u.source.id: u.source.homepage for u in units},
        cadence_hours={u.source.id: reg.cadence_hours(u.source) for u in units},
        history=hist,
        live_records=len(live),
        outside_records=outside,
        msa_pop_m=m.msa_pop_m if m else None,
        curated_sources={u.source.id for u in units if u.source.adapter == "curated"},
    )


def gate_city(
    db: Database, reg: Registry, city: CityConfig, now: datetime, events: list[Event], persist: bool = True
) -> CityCoverage:
    """Evaluate + apply hysteresis (+ persist the tier and log transitions when ``persist``)."""
    cov = evaluate(gather(db, reg, city, now, events))
    row = db.one("SELECT * FROM city_gate WHERE city = ?", (city.slug,))
    prev = row["tier"] if row else None
    m = metros().get(city.slug)
    tier, failing_since, banner = decide_tier(
        cov,
        city.enabled,
        prev,
        parse_iso(row["failing_since"]) if row else None,
        bool(m and m.incumbent),
        now,
    )
    cov = cov.model_copy(update={"tier": tier, "failing_since": failing_since, "banner": banner})
    if persist:
        since = row["since"] if row and prev == tier else iso(now)
        db.execute(
            "INSERT INTO city_gate (city, tier, since, failing_since, evaluated_at, data) VALUES (?,?,?,?,?,?)"
            " ON CONFLICT(city) DO UPDATE SET tier=excluded.tier, since=excluded.since,"
            " failing_since=excluded.failing_since, evaluated_at=excluded.evaluated_at, data=excluded.data",
            (city.slug, tier, since, iso(failing_since) if failing_since else None, iso(now), cov.model_dump_json()),
        )
        if prev != tier:
            level = "warn" if tier != "live" else "info"
            why = "; ".join(cov.reasons[:3]) or "all hard criteria pass"
            hlog(db, f"gate@{city.slug}", level, "gate_tier", f"{prev or 'new'} → {tier}: {why}"[:500], now)
    return cov
