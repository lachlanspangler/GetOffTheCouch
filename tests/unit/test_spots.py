from datetime import UTC, datetime

from gotc.pipeline.build import apply_spots
from gotc.schema import Event, SourceEvent

T = datetime(2026, 10, 20, 23, tzinfo=UTC)


def event(**kw):
    d = {
        "id": "e",
        "city": "c",
        "title": "Knitting Circle",
        "kind": "one_off",
        "category": "arts.workshop",
        "start": T,
        "timezone": "America/Chicago",
        "location": {},
        "price": {},
        "sources": [],
        "first_seen": T,
        "last_checked": T,
    }
    d.update(kw)
    return Event.model_validate(d)


def member(**extras):
    return SourceEvent(
        source_id="lib",
        record_id="1",
        city="c",
        title="Knitting Circle",
        category="arts.workshop",
        start=T,
        timezone="America/Chicago",
        fetched_at=T,
        extras=extras,
    )


def test_reported_spots_become_exact_pct_left_attendance_and_derived_deadline():
    ev = event(tags=["registration_required"])
    apply_spots(ev, [member(capacity=20, registered=17)])
    assert ev.tickets.pct_left and ev.tickets.pct_left.mid == 15 and "17 of 20" in ev.tickets.pct_left.method
    assert ev.tickets.selling_fast and "3 of 20" in (ev.tickets.signal or "")
    assert ev.attendance and ev.attendance.mid == 17 and ev.attendance.high == 20
    assert ev.registration and ev.registration.method == "derived" and ev.registration.closes_at == T


def test_full_closes_registration():
    ev = event()
    apply_spots(ev, [member(capacity=15, registered=15)])
    assert ev.tickets.availability == "registration_closed"


def test_no_counts_no_signal_but_required_gets_derived_deadline():
    ev = event(tags=["registration_required"])
    apply_spots(ev, [member()])
    assert ev.tickets.pct_left is None
    assert ev.registration and ev.registration.confidence == 0.5
    plain = event()
    apply_spots(plain, [member()])
    assert plain.registration is None


def test_spots_left_without_capacity():
    ev = event()
    apply_spots(ev, [member(spots_left=2)])
    assert ev.tickets.spots_left == 2 and ev.tickets.spots_total is None and ev.tickets.selling_fast
    assert ev.tickets.pct_left is None  # no total → no percentage, never a guess
