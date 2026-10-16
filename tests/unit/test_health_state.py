from datetime import UTC, datetime, timedelta

from gotc.health.state import Health, Outcome, is_stale, judge, transition

T0 = datetime(2026, 10, 16, tzinfo=UTC)
CAD = timedelta(hours=24)


def ok(n=50, rej=0, complete=True):
    return Outcome(ok=True, valid=n, rejected=rej, complete=complete)


def fail(kind="server_error"):
    return Outcome(ok=False, error_kind=kind, error=f"{kind}!")


def test_first_success_is_healthy_and_schedules_next():
    v = transition(Health(), ok(), T0, CAD, 1)
    assert v.health.state == "healthy"
    assert v.health.next_due_at == T0 + CAD
    assert v.apply_snapshot


def test_three_failures_quarantine_with_backoff_then_recover_after_two_successes():
    h = transition(Health(), ok(), T0, CAD, 1).health
    states = []
    for i in range(4):
        v = transition(h, fail(), T0 + timedelta(hours=i), CAD, 1)
        h = v.health
        states.append(h.state)
        assert not v.apply_snapshot
    assert states == ["degraded", "degraded", "quarantined", "quarantined"]
    # backoff doubles while quarantined
    assert h.next_due_at - (T0 + timedelta(hours=3)) == CAD * 2
    h = transition(h, ok(), T0 + timedelta(days=3), CAD, 1).health
    assert h.state == "recovering"
    h = transition(h, ok(), T0 + timedelta(days=4), CAD, 1).health
    assert h.state == "healthy"


def test_schema_drift_is_a_failure_even_on_http_200():
    o = judge(ok(n=2, rej=8), expect_min=1, baseline=10)
    assert not o.ok and o.error_kind == "schema_drift"


def test_empty_results_is_a_failure():
    o = judge(ok(n=0), expect_min=1, baseline=None)
    assert not o.ok and o.error_kind == "empty_results"
    assert judge(ok(n=0), expect_min=0, baseline=None).ok


def test_volume_drop_degrades_keeps_baseline_and_blocks_deletions():
    h = Health(state="healthy", baseline_count=100.0)
    v = transition(h, ok(n=10), T0, CAD, 1)
    assert v.health.state == "degraded"
    assert v.health.baseline_count == 100.0
    assert not v.apply_snapshot
    assert any(e[1] == "volume_drop" for e in v.events)


def test_incomplete_fetch_never_applies_snapshot():
    assert not transition(Health(), ok(complete=False), T0, CAD, 1).apply_snapshot


def test_transitions_are_logged():
    h = Health(state="healthy", consecutive_failures=2)
    v = transition(h, fail(), T0, CAD, 1)
    kinds = [e[1] for e in v.events]
    assert "server_error" in kinds and "healthy->quarantined" in kinds


def test_staleness():
    assert is_stale(Health(), T0, CAD)
    assert not is_stale(Health(last_success_at=T0 - timedelta(hours=1)), T0, CAD)
    assert is_stale(Health(last_success_at=T0 - timedelta(hours=25)), T0, CAD)
