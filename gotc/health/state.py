"""Per-unit health state machine. Pure functions — no I/O — so every transition is unit-tested.

        success                 failure (<3 in a row)
  ┌────────────────┐        ┌──────────────────────┐
  ▼                │        ▼                      │
healthy ──failure──► degraded ──3rd failure──► quarantined ──probe ok──► recovering ──2 ok──► healthy
                                                   ▲  │ probe fails: backoff doubles      │ fail
                                                   └──┴───────────────────────────────────┘

Checks applied to *successful* fetches (a 200 can still be broken):
  * schema_drift   — more than half of a ≥5-record batch failed SourceEvent validation
  * empty_results  — zero valid records where we expect some (layout change, silent API change)
  * volume_drop    — fewer than 30% of the usual count (EWMA baseline) → degraded, data kept, no deletions

Quarantined units keep serving last-known-good data, marked stale once older than the SLA.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Literal

State = Literal["healthy", "degraded", "quarantined", "recovering", "disabled", "never_run"]

QUARANTINE_AFTER = 3
RECOVER_AFTER = 2
EWMA_ALPHA = 0.3
MAX_PROBE_BACKOFF = timedelta(days=3)


@dataclass(frozen=True)
class Health:
    state: State = "never_run"
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_error_kind: str | None = None
    last_error: str | None = None
    next_due_at: datetime | None = None
    last_count: int | None = None
    baseline_count: float | None = None
    reason: str | None = None


@dataclass(frozen=True)
class Outcome:
    ok: bool
    valid: int = 0
    rejected: int = 0
    complete: bool = True
    error_kind: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class Verdict:
    health: Health
    events: list[tuple[str, str, str]]  # (level, kind, message) for the health log
    apply_snapshot: bool  # safe to mark records absent from this fetch as gone?


def judge(outcome: Outcome, expect_min: int, baseline: float | None) -> Outcome:
    """Turn a 'successful' fetch into a failure when its content is clearly broken."""
    if not outcome.ok:
        return outcome
    total = outcome.valid + outcome.rejected
    if total >= 5 and outcome.rejected / total > 0.5:
        return replace(
            outcome,
            ok=False,
            error_kind="schema_drift",
            error=f"{outcome.rejected}/{total} records failed validation",
        )
    if outcome.valid == 0 and expect_min > 0:
        return replace(outcome, ok=False, error_kind="empty_results", error="0 valid records returned")
    return outcome


def transition(h: Health, outcome: Outcome, now: datetime, cadence: timedelta, expect_min: int) -> Verdict:
    o = judge(outcome, expect_min, h.baseline_count)
    events: list[tuple[str, str, str]] = []
    if o.ok:
        baseline = (
            float(o.valid) if h.baseline_count is None else (1 - EWMA_ALPHA) * h.baseline_count + EWMA_ALPHA * o.valid
        )
        dropped = h.baseline_count is not None and h.baseline_count >= 20 and o.valid < 0.3 * h.baseline_count
        succ = h.consecutive_successes + 1
        if h.state in ("quarantined", "recovering"):
            state: State = "healthy" if succ >= RECOVER_AFTER else "recovering"
        else:
            state = "degraded" if dropped else "healthy"
        if dropped:
            events.append(
                (
                    "warn",
                    "volume_drop",
                    f"{o.valid} records vs usual ~{h.baseline_count:.0f}; kept data, no deletions",
                )
            )
        if state != h.state and h.state != "never_run":
            events.append(("info", f"{h.state}->{state}", f"recovered after {h.consecutive_failures} failure(s)"))
        new = replace(
            h,
            state=state,
            consecutive_failures=0,
            consecutive_successes=succ,
            last_attempt_at=now,
            last_success_at=now,
            last_count=o.valid,
            baseline_count=baseline if not dropped else h.baseline_count,  # don't learn from a broken run
            next_due_at=now + cadence,
            reason=None,
        )
        return Verdict(new, events, apply_snapshot=o.complete and not dropped)

    fails = h.consecutive_failures + 1
    kind = o.error_kind or "error"
    level = "error"
    if h.state in ("quarantined", "recovering") or fails >= QUARANTINE_AFTER:
        state = "quarantined"
        backoff = min(cadence * (2 ** max(0, fails - QUARANTINE_AFTER)), MAX_PROBE_BACKOFF)
        next_due = now + max(backoff, timedelta(hours=1))
    else:
        state = "degraded"
        next_due = now + min(cadence, timedelta(hours=1))  # retry soon, but not in a hot loop
        level = "warn"
    events.append((level, kind, o.error or kind))
    if state != h.state:
        events.append((level, f"{h.state}->{state}", f"{fails} consecutive failure(s); serving last-known-good"))
    new = replace(
        h,
        state=state,
        consecutive_failures=fails,
        consecutive_successes=0,
        last_attempt_at=now,
        last_failure_at=now,
        last_error_kind=kind,
        last_error=(o.error or "")[:500],
        next_due_at=next_due,
        reason=None,
    )
    return Verdict(new, events, apply_snapshot=False)


def disabled(h: Health, now: datetime, reason: str) -> Health:
    return replace(h, state="disabled", reason=reason, last_attempt_at=now)


def is_stale(h: Health, now: datetime, sla: timedelta) -> bool:
    return h.last_success_at is None or now - h.last_success_at > sla
