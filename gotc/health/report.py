"""Generate docs/HEALTH.md — the at-a-glance health of every unit, plus what to do about it."""

from __future__ import annotations

from datetime import datetime, timedelta

from gotc.config import Registry
from gotc.health.reliability import Reliability, reliability
from gotc.health.store import load_health
from gotc.storage.db import Database, iso

ICON = {
    "healthy": "🟢",
    "recovering": "🟡",
    "degraded": "🟠",
    "quarantined": "🔴",
    "disabled": "⚪",
    "never_run": "⚫",
}

ACTION = {
    "auth": "check the API key / its quota",
    "forbidden": "403 — check robots.txt/ToS; we may be blocked or the endpoint moved",
    "not_found": "endpoint/dataset moved — find its new URL and update config",
    "rate_limited": "slow down: raise cadence_hours or add a host interval",
    "server_error": "upstream outage — usually self-heals; probe continues with backoff",
    "timeout": "upstream slow — usually self-heals",
    "network": "network error — usually self-heals",
    "schema_drift": "fields changed — inspect `rejects` and the latest raw payload, fix the parser, `gotc replay`",
    "empty_results": "0 records — layout/API change or a too-strict filter; inspect the latest raw payload",
    "format_changed": "payload no longer parses — inspect raw payload, update adapter",
    "robots_disallowed": "robots.txt now disallows us — disable the source; do not work around it",
    "adapter_crash": "bug in the adapter — see build.log traceback, add a regression test",
    "config": "config error — fix config/ YAML",
}


def _rel(r: Reliability | None) -> str:
    if r is None:
        return "–"
    return f"{r.grade} ({r.score:.0f})" if r.score is not None else f"– ({r.attempts} runs)"


def render(db: Database, reg: Registry, now: datetime, extra: list[str] | None = None) -> str:
    lines = [
        "# Health",
        "",
        f"_Generated {iso(now)} by `gotc` (do not edit by hand — regenerated every run)._",
        "",
    ]
    units = reg.units()
    rel = reliability(db, now)
    rows = []
    counts: dict[str, int] = {}
    for u in units:
        h = load_health(db, u.key)
        counts[h.state] = counts.get(h.state, 0) + 1
        sla = timedelta(hours=reg.sla_hours(u.source))
        stale = h.state != "disabled" and (h.last_success_at is None or now - h.last_success_at > sla)
        age = f"{(now - h.last_success_at).total_seconds() / 3600:.1f}h" if h.last_success_at else "never"
        rows.append(
            (
                {
                    "quarantined": 0,
                    "degraded": 1,
                    "recovering": 2,
                    "never_run": 3,
                    "healthy": 4,
                    "disabled": 5,
                }[h.state],
                f"| {ICON[h.state]} {h.state} | `{u.key}` | {age}{' ⚠️ stale' if stale else ''} | "
                f"{h.last_count if h.last_count is not None else '–'} | {h.consecutive_failures} | "
                f"{_rel(rel.get(u.key))} | "
                f"{(h.reason or h.last_error or '').replace('|', '/')[:120]} |",
                h,
                u.key,
            )
        )
    summary = " · ".join(f"{ICON[k]} {k}: {v}" for k, v in sorted(counts.items()))
    lines += [f"**{len(units)} units** — {summary}", ""]
    lines += [
        "| State | Unit | Last success | Records | Fails | Reliability (30d) | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    lines += [r[1] for r in sorted(rows, key=lambda r: (r[0], r[3]))]
    problems = [(r[2], r[3]) for r in rows if r[2].state in ("quarantined", "degraded")]
    if problems:
        lines += ["", "## Needs attention", ""]
        for h, key in problems:
            kind = h.last_error_kind or "error"
            lines.append(
                f"- `{key}` — **{kind}**: {ACTION.get(kind, 'investigate')}. Last error: `{(h.last_error or '')[:200]}`"
            )
    gates = db.all("SELECT city, tier, failing_since, data FROM city_gate ORDER BY city")
    if gates:
        import json

        lines += [
            "",
            "## Go-live gate (ADR-0008)",
            "",
            "| City | Tier | Failing hard since | Hard misses |",
            "|---|---|---|---|",
        ]
        for g in gates:
            reasons = [r.split(":")[0] for r in json.loads(g["data"]).get("reasons", []) if not r.startswith("thin:")]
            lines.append(f"| {g['city']} | {g['tier']} | {g['failing_since'] or '–'} | {', '.join(reasons) or '–'} |")
    rej = db.all(
        "SELECT unit, COUNT(*) n, MAX(error) sample FROM rejects WHERE at >= ? GROUP BY unit ORDER BY n DESC LIMIT 15",
        (iso(now - timedelta(days=2)),),
    )
    if rej:
        lines += [
            "",
            "## Rejected records (last 48h)",
            "",
            "| Unit | Rejects | Sample error |",
            "|---|---|---|",
        ]
        lines += [f"| `{r['unit']}` | {r['n']} | {str(r['sample'])[:140].replace('|', '/')} |" for r in rej]
    log = db.all("SELECT at, unit, level, kind, message FROM health_log ORDER BY id DESC LIMIT 25")
    if log:
        lines += ["", "## Recent health log", ""]
        lines += [f"- {r['at']} · {r['level']} · `{r['unit']}` · {r['kind']}: {r['message'][:160]}" for r in log]
    if extra:
        lines += ["", "## Doctor", "", *extra]
    return "\n".join(lines) + "\n"
