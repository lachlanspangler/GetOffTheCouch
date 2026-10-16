"""Ranking hints (gotc/pipeline/rankprep.py). Titles are real ones from the 2026-10-16 exports
(source noted next to each), not invented look-alikes."""

from datetime import UTC, datetime, timedelta

from gotc.pipeline.rankprep import (
    annotate,
    best_reliability,
    completeness,
    fingerprint,
    low_quality,
    norm_title,
    quality_flags,
)
from gotc.schema import Event

NOW = datetime(2026, 10, 16, 13, tzinfo=UTC)
T = datetime(2026, 10, 18, 0, tzinfo=UTC)  # Sat Oct 17, 7pm Chicago


def event(**kw):
    d = {
        "id": "e",
        "city": "minneapolis",
        "title": "Show",
        "kind": "one_off",
        "category": "music.concert",
        "start": T,
        "timezone": "America/Chicago",
        "location": {"venue_name": "Icehouse Minneapolis", "lat": 44.95, "lon": -93.28},
        "price": {"min": 15},
        "url": "https://example.org/e",
        "sources": [{"source_id": "icehouse_mpls", "record_id": "1", "fetched_at": NOW}],
        "first_seen": NOW,
        "last_checked": NOW,
    }
    d.update(kw)
    return Event.model_validate(d)


def flags(e: Event, desc: int = 200, series: int = 0) -> list[str]:
    return quality_flags(e, desc, series)


def test_admin_noise_titles():
    assert "admin" in flags(event(title="Board Meeting"))  # mprb_events
    assert "admin" in flags(event(title="Teen Library Advisory Committee"))  # mdpls_events
    assert "admin" in flags(event(title="King County Parks and Recreation Office Hours"))  # kcls_events
    closed = flags(event(title="Closed for private event"))  # cedar_cultural_center: two phrases
    assert "admin" in closed and "hard_noise" in closed
    # a charity dinner run by a committee is not a committee meeting (uwkc_volunteer)
    assert "admin" not in flags(event(title="International Rescue Committee's Annual Benefit Dinner, 21+"))


def test_cancelled_title_is_hard_noise():
    f = flags(event(title="CANCELED: Yoga"))  # nyc parks
    assert "cancelled_title" in f and "hard_noise" in f
    assert low_quality(f) == 1.0


def test_promo_needs_a_real_promo_phrase():
    # chipublib: "Promoting" is not a promo code
    assert "promo" not in flags(event(title="Non-Traditional Skateboarding: Preserving and Promoting Our History"))
    assert "promo" in flags(event(title="Comedy night: use code LAUGH for 20% off"))


def test_caps_and_shouty():
    assert "all_caps" in flags(event(title="TERRAPIN STALLION (PRIMAL GRATEFUL DEAD & WEEN TRIBUTE)"))  # icehouse
    assert "all_caps" not in flags(event(title="Food Packers-Eagan"))  # handson_twin_cities
    assert "shouty" in flags(event(title="House Sessions feat. Michael Grey, Alexis Rose & TNA!!!"))  # icehouse


def test_generic_title_no_info_no_place():
    assert "generic_title" in flags(event(title="Program"))
    bare = event(title="Street Health Outreach and Wellness", url=None, price={}, location={})  # nyc permits
    f = flags(bare, desc=0)
    assert "no_info" in f and "no_place" in f
    online = event(title="Virtual author talk", location={})
    assert "no_place" not in flags(online)


def test_long_span_and_recurring_noise():
    span = event(title="Fulfilling Senior Holiday Wishes", end=T + timedelta(days=30))  # handson_twin_cities
    assert "long_span" in flags(span)
    exhibit = event(category="arts.museum", end=T + timedelta(days=60))
    assert "long_span" not in flags(exhibit)
    assert "noise_recurring" in flags(event(title="Baby Storytime", category="family.kids"), series=20)  # hclib
    assert "noise_recurring" not in flags(event(title="Trivia", category="trivia_games.trivia"), series=20)
    assert low_quality(["noise_recurring", "no_place", "no_info"]) == 1.0


def test_completeness_bits():
    full = event(end=T + timedelta(hours=2))
    assert completeness(full, 120) == 1.0
    empty = event(location={}, price={}, url=None, category="other.uncategorized")
    assert completeness(empty, 0) == 0.0
    assert completeness(event(location={"venue_name": "TBD"}), 120) < completeness(event(), 120)


def test_fingerprint_is_title_place_day():
    a = event(id="a", title="Food Packers-Eagan")
    b = event(id="b", title="Food Packers - Eagan", start=T + timedelta(hours=3))  # later shift, same day
    c = event(id="c", title="Food Packers-Eagan", start=T + timedelta(days=1))
    assert norm_title("Baby Storytime (ages 0-2)") == "baby storytime"
    assert fingerprint(a) == fingerprint(b)
    assert fingerprint(a) != fingerprint(c)


def test_annotate_near_dups_groups_and_reliability():
    lib = "Hennepin County Library"
    evs = [
        event(id="r", title="Baby Storytime", organizer=lib, location={"venue_name": "HCL – Roosevelt"}),
        event(id="n", title="Baby Storytime", organizer=lib, location={"venue_name": "HCL – Northeast"}),
        event(id="w", title="Baby Storytime", organizer=lib, location={"venue_name": "HCL – Walker"}),
        event(id="t1", title="Trivia Night", venue_id="ven_1"),
        event(id="t2", title="Trivia Night!", venue_id="ven_1"),  # near-dup: Jaccard ≥ 0.8
        event(id="x", title="Something else", summary="x" * 90),
    ]
    out = {e.id: e.rank for e in annotate(evs, {"icehouse_mpls": 92.0}, NOW)}
    assert all(h is not None for h in out.values())
    assert out["r"].group == out["n"].group == out["w"].group and out["r"].group_n == 3
    assert out["x"].group is None and out["x"].group_n == 1
    assert out["t1"].fp == out["t2"].fp
    assert out["x"].desc_len == 90 and out["x"].src_rel == 0.92
    assert out["x"].quality == round(out["x"].complete * (1 - out["x"].lowq), 2)


def test_best_reliability_unknown_is_none():
    e = event(sources=[{"source_id": "a", "record_id": "1", "fetched_at": NOW}])
    assert best_reliability(e, {"a": None}) is None
    assert best_reliability(e, {}) is None
