"""A long run exports its next 8 dates plus a summary (the 42 MB NYC feed: 3,401 Balloon Museum entry slots)."""

from __future__ import annotations

from datetime import timedelta

from gotc.pipeline.build import SERIES_EXPORT_CAP, cap_series
from gotc.schema import Event, EventKind, Location, Price, Registration, SourceRef
from tests.conftest import NOW


def ev(i: int, series: str | None = "ser_a", **kw) -> Event:
    return Event(
        id=f"e{i}",
        city="nyc",
        title="Balloon Museum NYC",
        kind=EventKind.RECURRING,
        category="arts.museum",
        start=NOW + timedelta(hours=3 * i + 1),
        timezone="America/New_York",
        location=Location(),
        price=Price(),
        sources=[SourceRef(source_id="ticketmaster", record_id=str(i), fetched_at=NOW)],
        first_seen=NOW,
        last_checked=NOW,
        series_id=series,
        **kw,
    )


def test_a_long_series_keeps_its_next_dates_and_says_how_many_more():
    items = [(ev(i), None) for i in range(40)] + [(ev(100, series=None), None)]
    out = cap_series(items, NOW)  # type: ignore[arg-type]
    kept = [e for e, _ in out if e.series_id]
    assert [e.id for e in kept] == [f"e{i}" for i in range(SERIES_EXPORT_CAP)]
    assert all(e.series_total == 40 and e.series_last == NOW + timedelta(hours=3 * 39 + 1) for e in kept)
    assert any(e.id == "e100" for e, _ in out)  # not a series: untouched


def test_short_series_and_open_registrations_are_never_folded():
    short = [(ev(i, series="ser_b"), None) for i in range(5)]
    assert cap_series(short, NOW) == short  # type: ignore[arg-type]
    reg = Registration(closes_at=NOW + timedelta(days=30))
    items = [(ev(i), None) for i in range(20)]
    items[15][0].registration = reg
    out = {e.id for e, _ in cap_series(items, NOW)}  # type: ignore[arg-type]
    assert "e15" in out and len(out) == SERIES_EXPORT_CAP + 1
