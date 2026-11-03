"""Ingest: run one unit (source × city) end to end — fetch, store raw, parse, validate, upsert, judge health.

Each unit commits in its own transaction, so a run killed halfway loses at most the unit in flight;
re-running simply picks up the units that are still due (``next_due_at`` <= now). That is the whole
resumability story — no checkpoint files, no locks to clean up.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from pydantic import ValidationError

from gotc.adapters.base import (
    Adapter,
    AdapterConfigError,
    FetchContext,
    MissingCredentials,
    ParseContext,
    Payload,
    get_adapter,
)
from gotc.config import Registry, Unit
from gotc.health import store as hstore
from gotc.health.state import Outcome, disabled, transition
from gotc.http.client import FetchError, PoliteClient
from gotc.pipeline.category_basis import ensure_basis
from gotc.pipeline.normalize import _MATCHUP, audience_skip, location_skip, normalize_record
from gotc.schema import SourceEvent
from gotc.settings import Settings
from gotc.storage.db import Database, iso
from gotc.storage.raw import RawStore
from gotc.taxonomy import taxonomy

log = logging.getLogger(__name__)


@dataclass
class UnitResult:
    unit: str
    status: str  # ok | failed | skipped | disabled
    fetched: int = 0
    valid: int = 0
    rejected: int = 0
    error_kind: str | None = None
    error: str | None = None
    state: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class Parsed:
    valid: list[tuple[SourceEvent, int | None]] = field(default_factory=list)  # (event, raw_fetch_id)
    rejects: list[tuple[str, str, int | None]] = field(default_factory=list)  # (hint, error, raw_fetch_id)
    skipped: int = 0  # valid records deliberately left out (e.g. not open to the public)
    #: why each skipped record was left out: (record_id, title, start, rule, reason) — quarantined, never silent
    skips: list[tuple[str, str, str | None, str, str]] = field(default_factory=list)


def campus_catchall(rec: dict[str, Any], params: dict[str, Any]) -> bool:
    """Institution feeds are noisy (benefits enrollment, fellowships, office notices). An item that only reached
    the feed's catch-all category is skipped — precision over recall for campus calendars."""
    if params.get("audience_filter") != "institution" or "_reject" in rec:
        return False
    return rec.get("category") in (params.get("default_category"), "other.uncategorized")


# University calendars are mostly internal (club meetings, office hours, dorm socials). For institution feeds only
# public-facing families pass unless the source lists its own `allow_families`.
INSTITUTION_FAMILIES = ("music", "arts", "sports_watch", "learning", "community", "outdoors", "fitness", "niche")


def campus_allowlist(category: str, params: dict[str, Any]) -> bool:
    """True when an institution-feed record should be kept (its family is public-facing)."""
    if params.get("audience_filter") != "institution":
        return True
    if category == "other.uncategorized":
        # with catch-all defaults gone (ADR-0010), uncategorized campus listings are about half real talks and
        # exhibitions: the build-time gate judges them on their own text and tags instead of dropping them here
        return True
    allow = params.get("allow_families") or INSTITUTION_FAMILIES
    return category.split(".", 1)[0] in allow


def _iso(v: Any) -> str | None:
    if v is None:
        return None
    return v.isoformat() if isinstance(v, datetime) else str(v)


def _ingest_skip(rec: dict[str, Any], params: dict[str, Any]) -> tuple[str, str] | None:
    """(rule, reason) when a parsed record is left out before storage, else None."""
    # (campus_catchall is no longer applied: with catch-all defaults gone, "uncategorized" campus listings are about
    #  half real events — data review 2026-11-02 — so they publish as uncategorized and the build-time gate judges them)
    if why := audience_skip(rec, params.get("audience_filter")):
        return "ingest:audience", f"campus feed: {why}"
    if why := location_skip(rec, params.get("exclude_location")):
        return "ingest:location", why
    return None


def store_ingest_skips(
    db: Database, unit: Unit, skips: list[tuple[str, str, str | None, str, str]], now: datetime
) -> None:
    """Replace this unit's ingest-stage quarantine with this fetch's skips (snapshot, like source_records)."""
    db.execute(
        "DELETE FROM gated_listings WHERE source_id = ? AND city = ? AND stage = 'ingest'",
        (unit.source.id, unit.city.slug),
    )
    for rid, title, start, rule, reason in skips:
        db.execute(
            "INSERT OR REPLACE INTO gated_listings (city, source_id, record_id, stage, title, start_at, rule, family,"
            " reason, evidence, gated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                unit.city.slug,
                unit.source.id,
                rid,
                "ingest",
                title or "(untitled)",
                start,
                rule,
                "ingest_filter",
                reason,
                None,
                iso(now),
            ),
        )


def parse_payloads(
    adapter: Adapter, unit: Unit, payloads: list[tuple[Payload, int | None]], fetched_at: datetime
) -> Parsed:
    """Pure parse + validate. Shared by live ingest and ``replay``."""
    pctx = ParseContext(unit=unit, fetched_at=fetched_at)
    tax = taxonomy()
    out = Parsed()
    seen: set[str] = set()
    for payload, raw_id in payloads:
        try:
            records = list(adapter.parse(payload, pctx))
        except Exception as e:  # a parser crash on one payload is drift, not a reason to lose the rest
            out.rejects.append(("<payload>", f"parser crashed: {type(e).__name__}: {e}", raw_id))
            continue
        for rec in records:
            if "_reject" in rec:
                out.rejects.append((str(rec.get("_hint", ""))[:200], str(rec["_reject"]), raw_id))
                continue
            why = _ingest_skip(rec, unit.source.params)
            if why is not None:
                out.skipped += 1
                rid = rec.get("record_id") or f"_hint:{rec.get('_hint') or rec.get('title') or len(out.skips)}"
                out.skips.append((str(rid), str(rec.get("title") or "")[:300], _iso(rec.get("start")), *why))
                continue
            try:
                rec = normalize_record(rec, unit.source.name)
                # an arena's "basketball" is a game to watch, not a rec league
                spectator = unit.source.params.get("spectator_venue")
                if (
                    unit.source.params.get("audience_filter") == "institution"
                    and str(rec.get("category", "")).startswith("sports_league.")
                    and _MATCHUP.search(str(rec.get("title") or ""))
                ):
                    # a campus "Volleyball vs Ole Miss" is a game to watch, not a rec league to join (2026-11-02)
                    rec["category"] = "sports_watch.game"
                    rec["category_basis"], rec["category_note"] = "classified", "a campus matchup ('A vs B') is a game"
                if spectator and str(rec.get("category", "")).startswith("sports_league."):
                    rec["category"] = "sports_watch.game"
                    rec["category_basis"] = "source_kind"
                    rec["category_note"] = "a sport at a spectator venue is a game to watch (our config)"
                ev = SourceEvent.model_validate(rec)
                if not tax.is_valid(ev.category):
                    raise ValueError(f"unknown category {ev.category!r}")
                ev.category = tax.resolve(ev.category)
                ev.tags = tax.valid_tags(ev.tags)
                ensure_basis(ev, unit.source.params, tax, unit.source.adapter)
                if not campus_allowlist(ev.category, unit.source.params):
                    out.skipped += 1
                    out.skips.append(
                        (
                            ev.record_id,
                            ev.title,
                            ev.start.isoformat(),
                            "ingest:campus_family",
                            f"campus feed: {ev.category.split('.', 1)[0]} isn't one of this source's public-facing"
                            " families",
                        )
                    )
                    continue
            except (ValidationError, ValueError) as e:
                hint = f"{rec.get('record_id')}: {str(rec.get('title'))[:80]}"
                out.rejects.append((hint, _short_error(e), raw_id))
                continue
            if ev.record_id in seen:
                continue
            seen.add(ev.record_id)
            out.valid.append((ev, raw_id))
    return out


def run_unit(
    db: Database,
    reg: Registry,
    unit: Unit,
    http: PoliteClient,
    settings: Settings,
    now: datetime,
    run_id: int | None = None,
    force: bool = False,
) -> UnitResult:
    key = unit.key
    h = hstore.load_health(db, key)
    cadence = jittered(timedelta(hours=reg.cadence_hours(unit.source)), key)

    if not unit.source.enabled:
        with db.tx():
            hstore.save_health(db, unit, disabled(h, now, "disabled in config"))
        return UnitResult(key, "disabled", notes=["disabled in config"])
    if missing := reg.missing_requirements(unit.source):
        reason = f"needs {', '.join(missing)}"
        with db.tx():
            if h.state != "disabled" or h.reason != reason:
                hstore.log(db, key, "warn", "disabled", reason, now)
            hstore.save_health(db, unit, disabled(h, now, reason))
        return UnitResult(key, "disabled", notes=[reason], state="disabled")
    if not force and h.next_due_at and h.next_due_at > now and h.state != "disabled":
        return UnitResult(key, "skipped", state=h.state, notes=[f"next due {iso(h.next_due_at)}"])

    adapter = get_adapter(unit.source.adapter)
    apply_rate_limit(http, unit)
    raw = RawStore(settings.raw_dir)
    ctx = FetchContext(unit=unit, http=http, now=now, settings=settings, cursor=hstore.get_cursor(db, key))
    result = UnitResult(key, "ok")
    try:
        fr = adapter.fetch(ctx)
    except MissingCredentials as e:
        with db.tx():
            hstore.save_health(db, unit, disabled(h, now, str(e)))
        return UnitResult(key, "disabled", notes=[str(e)], state="disabled")
    except (FetchError, AdapterConfigError, ValueError, KeyError, json.JSONDecodeError) as e:
        kind = getattr(e, "kind", "config" if isinstance(e, AdapterConfigError) else "format_changed")
        return _fail(db, unit, h, now, cadence, run_id, kind, f"{type(e).__name__}: {e}")
    except Exception as e:  # unexpected adapter bug: still a health event, never a crashed run
        log.exception("adapter %s crashed", key)
        return _fail(db, unit, h, now, cadence, run_id, "adapter_crash", f"{type(e).__name__}: {e}")

    with db.tx():
        stored: list[tuple[Payload, int | None]] = []
        for p in fr.payloads:
            digest, rel = raw.put(unit.source.id, now, p.content, p.content_type)
            cur = db.execute(
                "INSERT INTO raw_fetches (run_id, unit, source_id, city, url, fetched_at, status, content_hash,"
                " path, bytes, elapsed_ms, from_cache) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    key,
                    unit.source.id,
                    unit.city.slug,
                    p.url,
                    iso(now),
                    p.status,
                    digest,
                    rel,
                    len(p.content),
                    p.elapsed_ms,
                    int(p.from_cache),
                ),
            )
            stored.append((p, cur.lastrowid))
        parsed = parse_payloads(adapter, unit, stored, now)
        result.fetched = len(fr.payloads)
        result.valid = len(parsed.valid)
        result.rejected = len(parsed.rejects)
        if parsed.skipped:
            result.notes.append(f"{parsed.skipped} not-public record(s) skipped")
        if fr.complete:  # a partial fetch (capped pages) only saw some records: keep the previous snapshot's skips
            store_ingest_skips(db, unit, parsed.skips, now)
        for hint, err, rid in parsed.rejects[:200]:
            db.execute(
                "INSERT INTO rejects (unit, raw_fetch_id, at, record_hint, error) VALUES (?,?,?,?,?)",
                (key, rid, iso(now), hint, err[:1000]),
            )
        outcome = Outcome(ok=True, valid=result.valid, rejected=result.rejected, complete=fr.complete)
        verdict = transition(h, outcome, now, cadence, unit.source.expect_min_records)
        if parsed.valid:  # even a drifting batch keeps its valid records
            upsert_records(db, unit, parsed, now)
        if verdict.apply_snapshot:
            gone = mark_gone(db, unit, {ev.record_id for ev, _ in parsed.valid}, now)
            if gone:
                result.notes.append(f"{gone} record(s) no longer listed → marked gone")
        if fr.cursor:
            hstore.set_cursor(db, key, fr.cursor)
        hstore.save_health(db, unit, verdict.health)
        for level, kind, msg in verdict.events:
            hstore.log(db, key, level, kind, msg, now)
        result.state = verdict.health.state
        if verdict.health.consecutive_failures:
            result.status = "failed"
            result.error_kind = verdict.health.last_error_kind
            result.error = verdict.health.last_error
        _record_run_unit(db, run_id, key, now, result)
    return result


def jittered(cadence: timedelta, key: str) -> timedelta:
    """Up to 10% earlier, deterministic per unit, so units that ran together don't all come due together."""
    frac = int(hashlib.sha1(key.encode()).hexdigest()[:4], 16) / 0xFFFF
    return cadence * (1 - 0.1 * frac)


def apply_rate_limit(http: PoliteClient, unit: Unit) -> None:
    """Per-source politeness: ``min_interval_s`` applies to every host named in the source's params."""
    if not unit.source.min_interval_s:
        return
    from urllib.parse import urlsplit

    p = unit.source.params
    urls = [p.get("base_url"), p.get("domain") and f"https://{p['domain']}", *_as_list(p.get("url"))]
    for u in filter(None, urls):
        host = urlsplit(str(u)).netloc
        http.host_intervals[host] = max(http.host_intervals.get(host, 0.0), unit.source.min_interval_s)


def _as_list(v: Any) -> list[Any]:
    return v if isinstance(v, list) else [v]


def upsert_records(db: Database, unit: Unit, parsed: Parsed, now: datetime) -> int:
    changed = 0
    for ev, raw_id in parsed.valid:
        data = ev.model_dump_json(exclude={"fetched_at"})
        digest = hashlib.sha256(data.encode()).hexdigest()[:20]
        full = ev.model_dump_json()
        cur = db.execute(
            "INSERT INTO source_records (source_id, record_id, city, unit, data, content_hash, raw_fetch_id,"
            " start_at, first_seen, last_seen, gone_at) VALUES (?,?,?,?,?,?,?,?,?,?,NULL)"
            " ON CONFLICT(source_id, record_id, city) DO UPDATE SET"
            " data=excluded.data, content_hash=excluded.content_hash, raw_fetch_id=excluded.raw_fetch_id,"
            " start_at=excluded.start_at, last_seen=excluded.last_seen, gone_at=NULL"
            " WHERE source_records.content_hash != excluded.content_hash OR source_records.gone_at IS NOT NULL"
            " OR source_records.last_seen != excluded.last_seen",
            (
                ev.source_id,
                ev.record_id,
                ev.city,
                unit.key,
                full,
                digest,
                raw_id,
                iso(ev.start),
                iso(now),
                iso(now),
            ),
        )
        changed += cur.rowcount
        _snapshot_prices(db, ev, now)
    return changed


def _snapshot_prices(db: Database, ev: SourceEvent, now: datetime) -> None:
    for o in ev.offers:
        if o.price_min is None and o.listing_count is None:
            continue
        db.execute(
            "INSERT OR IGNORE INTO price_snapshots (source_id, record_id, city, seller, observed_at, price_min,"
            " price_max, listing_count, availability) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                ev.source_id,
                ev.record_id,
                ev.city,
                o.seller,
                iso(now),
                o.price_min,
                o.price_max,
                o.listing_count,
                o.availability.value,
            ),
        )


def mark_gone(db: Database, unit: Unit, seen: set[str], now: datetime) -> int:
    """Records absent from a complete, healthy snapshot (and not long past) are marked gone."""
    rows = db.all(
        "SELECT record_id FROM source_records WHERE unit = ? AND gone_at IS NULL AND start_at >= ?",
        (unit.key, iso(now - timedelta(hours=24))),  # include things that started earlier today (all-day items)
    )
    gone = [r["record_id"] for r in rows if r["record_id"] not in seen]
    for rid in gone:
        db.execute(
            "UPDATE source_records SET gone_at = ? WHERE source_id = ? AND record_id = ? AND city = ?",
            (iso(now), unit.source.id, rid, unit.city.slug),
        )
    return len(gone)


def _fail(
    db: Database,
    unit: Unit,
    h: Any,
    now: datetime,
    cadence: timedelta,
    run_id: int | None,
    kind: str,
    message: str,
) -> UnitResult:
    verdict = transition(h, Outcome(ok=False, error_kind=kind, error=message), now, cadence, 0)
    result = UnitResult(unit.key, "failed", error_kind=kind, error=message, state=verdict.health.state)
    with db.tx():
        hstore.save_health(db, unit, verdict.health)
        for level, k, msg in verdict.events:
            hstore.log(db, unit.key, level, k, msg, now)
        _record_run_unit(db, run_id, unit.key, now, result)
    return result


def _record_run_unit(db: Database, run_id: int | None, key: str, now: datetime, r: UnitResult) -> None:
    if run_id is None:
        return
    db.execute(
        "INSERT OR REPLACE INTO run_units (run_id, unit, status, started_at, finished_at, fetched, valid,"
        " rejected, error_kind, error) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (run_id, key, r.status, iso(now), iso(now), r.fetched, r.valid, r.rejected, r.error_kind, r.error),
    )


def _short_error(e: Exception) -> str:
    if isinstance(e, ValidationError):
        parts = [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors()[:3]]
        return "; ".join(parts)
    return str(e)[:300]
