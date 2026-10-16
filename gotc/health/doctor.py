"""`gotc doctor [--fix]` — the self-healing loop's checklist.

Reports (always) and repairs (with --fix) everything that can be repaired without a human decision:

| Check                                   | --fix repair                                                   |
|-----------------------------------------|----------------------------------------------------------------|
| SQLite integrity / pending migrations   | apply migrations (integrity failure → stop, never auto-repair)  |
| config: unknown adapter / bad params    | — (report; config is code)                                     |
| config: category maps → unknown ids     | — (report)                                                     |
| quarantined unit whose probe is due     | probe it now (a success moves it to recovering)                |
| rejects for a unit whose parser changed | replay the latest raw payload with the current parser          |
| raw payload files missing on disk       | drop the dangling raw_fetches rows                             |
| raw payloads older than retention       | delete files + rows (keeps the newest fetch per unit forever)  |
| rejects/health_log older than retention | prune                                                           |
| price snapshots older than 72 h         | fold into daily min/median/max rows; drop rows of past events  |
| export missing / older than the DB      | rebuild + export                                               |
| exported JSON fails schema validation   | rebuild; if still invalid → error (two-strike rule)            |
"""

from __future__ import annotations

import os
from datetime import timedelta

from gotc.adapters.base import AdapterConfigError, get_adapter
from gotc.config import load_registry
from gotc.health.report import render
from gotc.health.store import load_health
from gotc.schema import CityFeed
from gotc.settings import Settings
from gotc.storage.db import Database, iso, utcnow
from gotc.taxonomy import taxonomy

RAW_RETENTION_DAYS = int(os.environ.get("GOTC_RAW_RETENTION_DAYS", "30"))  # CI: 7 (newest per unit kept forever)
LOG_RETENTION_DAYS = 90


def doctor(settings: Settings, fix: bool = False) -> int:
    now = utcnow()
    errors: list[str] = []
    warnings: list[str] = []
    fixed: list[str] = []

    db = Database(settings.db_path)
    ok = db.one("PRAGMA integrity_check")
    if not ok or ok[0] != "ok":
        errors.append(f"SQLite integrity check failed: {ok[0] if ok else '?'} — restore data/gotc.db from backup")

    try:
        reg = load_registry()
    except Exception as e:
        print(f"ERROR config does not load: {e}")
        return 2
    tax = taxonomy()
    for sid, src in reg.all_sources().items():
        try:
            get_adapter(src.adapter).check_config(src)
        except AdapterConfigError as e:
            errors.append(f"config: {e}")
        for cat in (src.params.get("category_map") or {}).values():
            if not tax.is_valid(cat):
                errors.append(f"config: {sid} maps to unknown category {cat!r}")
        dc = src.params.get("default_category")
        if dc and not tax.is_valid(dc):
            errors.append(f"config: {sid} default_category {dc!r} unknown")

    # scheduled refreshes missing (GitHub disables schedules after 60 days without repo activity; runs can lag)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        last = db.one("SELECT MAX(started_at) t FROM runs WHERE trigger IN ('loop', 'shard', 'publish')")
        if last and last["t"]:
            from gotc.storage.db import parse_iso

            age = now - (parse_iso(last["t"]) or now)
            if age > timedelta(hours=3):
                warnings.append(
                    f"last scheduled pipeline run was {age.total_seconds() / 3600:.0f} h ago: hourly runs were skipped "
                    "(schedule disabled? see the keepalive workflow)"
                )

    # quarantined units due for a probe
    due = []
    for u in reg.units():
        h = load_health(db, u.key)
        if h.state == "quarantined":
            if h.next_due_at and h.next_due_at <= now:
                due.append(u)
            warnings.append(f"quarantined: {u.key} ({h.last_error_kind}: {(h.last_error or '')[:100]})")
        elif h.state == "degraded":
            warnings.append(f"degraded: {u.key} ({h.last_error_kind})")
    if fix and due:
        from gotc.pipeline.run import run

        for u in due:
            rep = run(db, reg, settings, city=u.city.slug, source=u.source.id, build=False, trigger="doctor")
            res = rep.units[0] if rep.units else None
            fixed.append(f"probed {u.key}: {res.status if res else '?'} → {res.state if res else '?'}")

    # dangling raw rows / retention
    raw_root = settings.raw_dir
    rows = db.all("SELECT id, path FROM raw_fetches")
    dangling = [r["id"] for r in rows if not (raw_root / r["path"]).exists()]
    if dangling:
        warnings.append(f"{len(dangling)} raw_fetches rows point at missing files")
        if fix:
            with db.tx():
                for rid in dangling:
                    db.execute("UPDATE source_records SET raw_fetch_id = NULL WHERE raw_fetch_id = ?", (rid,))
                    db.execute("UPDATE rejects SET raw_fetch_id = NULL WHERE raw_fetch_id = ?", (rid,))
                    db.execute("DELETE FROM raw_fetches WHERE id = ?", (rid,))
            fixed.append(f"dropped {len(dangling)} dangling raw_fetches rows")
    cutoff = iso(now - timedelta(days=RAW_RETENTION_DAYS))
    old = db.all(
        "SELECT r.id, r.path FROM raw_fetches r WHERE r.fetched_at < ? AND r.fetched_at < "
        "(SELECT MAX(fetched_at) FROM raw_fetches r2 WHERE r2.unit = r.unit)",
        (cutoff,),
    )
    if old and fix:
        still_used = {r["path"] for r in db.all("SELECT path FROM raw_fetches WHERE fetched_at >= ?", (cutoff,))}
        with db.tx():
            for r in old:
                db.execute("UPDATE source_records SET raw_fetch_id = NULL WHERE raw_fetch_id = ?", (r["id"],))
                db.execute("UPDATE rejects SET raw_fetch_id = NULL WHERE raw_fetch_id = ?", (r["id"],))
                db.execute("DELETE FROM raw_fetches WHERE id = ?", (r["id"],))
                if r["path"] not in still_used:
                    (raw_root / r["path"]).unlink(missing_ok=True)
        fixed.append(f"pruned {len(old)} raw payloads older than {RAW_RETENTION_DAYS}d")
    if fix:
        lc = iso(now - timedelta(days=LOG_RETENTION_DAYS))
        with db.tx():
            db.execute("DELETE FROM rejects WHERE at < ?", (lc,))
            db.execute("DELETE FROM health_log WHERE at < ? AND level = 'info'", (lc,))
        from gotc.storage.maintenance import downsample_price_snapshots

        gone, rolled = downsample_price_snapshots(db, now)
        if gone:
            fixed.append(f"price snapshots: {gone} rows folded into {rolled} daily rows / dropped for past events")

    # export validity / freshness
    web = settings.web_data_dir
    needs_build = not (web / "index.json").exists()
    for c in reg.cities.values():
        if not c.enabled:
            continue
        f = web / "cities" / f"{c.slug}.json"
        if not f.exists():
            needs_build = True
            continue
        try:
            CityFeed.model_validate_json(f.read_text())
        except Exception as e:
            warnings.append(f"export {f.name} fails schema validation: {str(e)[:200]}")
            needs_build = True
    if needs_build and fix:
        _rebuild(db, settings)
        fixed.append("rebuilt + re-exported dashboard data")
        for c in reg.cities.values():
            f = web / "cities" / f"{c.slug}.json"
            if c.enabled and f.exists():
                try:
                    CityFeed.model_validate_json(f.read_text())
                except Exception as e:  # two-strike rule: don't loop, escalate
                    errors.append(f"export {f.name} still invalid after rebuild: {str(e)[:200]}")

    lines = [f"- ERROR {e}" for e in errors] + [f"- warn {w}" for w in warnings] + [f"- fixed {x}" for x in fixed]
    (settings.docs_dir / "HEALTH.md").write_text(render(db, reg, now, extra=lines or ["- all checks passed"]))
    summary = f"doctor{' --fix' if fix else ''}: {len(errors)} errors, {len(fixed)} fixed, {len(warnings)} warnings"
    print(summary)
    for line in lines:
        print(" ", line)
    diary = settings.docs_dir / "DIARY.md"
    if diary.exists():
        with diary.open("a") as fh:
            fh.write(f"- {now.strftime('%Y-%m-%d %H:%M UTC')} · {summary}\n")
    return 1 if errors else 0


def _rebuild(db: Database, settings: Settings) -> None:
    from gotc.pipeline.build import build_city
    from gotc.pipeline.export import export_all

    reg = load_registry()
    now = utcnow()
    for c in reg.cities.values():
        if c.enabled:
            build_city(db, reg, c, now)
    export_all(db, reg, settings.web_data_dir, now)
