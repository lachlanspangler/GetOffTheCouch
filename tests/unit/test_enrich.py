from datetime import UTC, datetime, timedelta

from gotc.pipeline.enrich import derive_tags, estimate_attendance, sig2, social_score, ticket_signal
from gotc.schema import Availability, Event, Offer, TicketSignal
from gotc.taxonomy import taxonomy

T = datetime(2026, 11, 1, 1, tzinfo=UTC)


def event(**kw):
    d = {
        "id": "e",
        "city": "c",
        "title": "Show",
        "kind": "one_off",
        "category": "music.concert",
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


def test_sig2():
    assert sig2(1187) == 1200
    assert sig2(0.0) == 0
    assert sig2(87) == 87


def test_attendance_from_capacity_and_availability():
    e = event(tickets=TicketSignal(availability=Availability.SOLD_OUT))
    est = estimate_attendance(e, taxonomy(), 1550, "wikidata", None)
    assert est.low <= est.mid <= est.high <= 1550
    assert "1,550" in est.method and est.confidence >= 0.5


def test_attendance_falls_back_to_category_prior_with_low_confidence():
    est = estimate_attendance(event(category="trivia_games.trivia"), taxonomy(), None, None, None)
    assert est.confidence < 0.3 and "prior" in est.method


def test_attendance_reported_wins():
    est = estimate_attendance(event(), taxonomy(), 1000, "x", 420)
    assert est.mid == 420 and "reported" in est.method


def snap(hours_ago, listings, price):
    return {
        "seller": "SeatGeek",
        "observed_at": (T - timedelta(hours=hours_ago)).isoformat(),
        "price_min": price,
        "price_max": None,
        "listing_count": listings,
        "availability": "on_sale",
    }


def test_selling_fast_from_listing_drop_and_price_trend():
    offers = [
        Offer(
            seller="SeatGeek",
            kind="resale",
            url="https://seatgeek.com/x",
            source_id="seatgeek",
            fetched_at=T,
            availability=Availability.ON_SALE,
        )
    ]
    e = event(offers=offers)
    sig, trend = ticket_signal(e, [snap(72, 200, 40), snap(48, 180, 45), snap(0, 90, 60)], T)
    assert sig.selling_fast and "down" in (sig.signal or "")
    assert sig.pct_left is not None and sig.pct_left.mid == 45 and "not seats" in sig.pct_left.method
    assert trend is not None and trend.direction == "up" and trend.change_pct == 50.0


def test_no_snapshots_no_fake_signal():
    sig, trend = ticket_signal(event(), [], T)
    assert sig.pct_left is None and not sig.selling_fast and trend is None


def test_derived_tags_and_social_score():
    e = event(
        category="sports_league.kickball",
        kind="recurring",
        price={"is_free": True},
        registration={"signup_types": ["free_agent", "team"]},
    )
    tags = derive_tags(e, "All skill levels welcome! 21+", taxonomy())
    for t in ("free", "recurring", "free_agent", "team_signup", "beginner_friendly", "21+", "solo_friendly"):
        assert t in tags
    e.tags = tags
    s = social_score(e, taxonomy())
    assert s.score >= 0.9 and any("free-agent" in r for r in s.reasons)


def test_free_food_tag():
    e = event(category="learning.tech")
    assert "free_food" in derive_tags(e, "Talk + Q&A. Pizza provided!", taxonomy())
    assert "free_food" not in derive_tags(e, "Food trucks on site", taxonomy())


def test_kids_teens_tag():
    def tags(title: str, body: str = "") -> list[str]:
        return derive_tags(event(category="arts.books", title=title), f"{title} {body}", taxonomy())

    assert "kids_teens" in tags("Teen Library Advisory Committee")
    assert "kids_teens" in tags("Toddler Storytime")
    assert "kids_teens" in tags("Homework Help at Sheridan Library (3rd-12th Grade)")
    assert "kids_teens" in tags("Craft Afternoon", "A program for kids ages 6-11.")
    assert "kids_teens" not in tags("Gentle Yoga with Melanie")
    assert "kids_teens" not in tags("Ali Wong Live", "Fresh off her special Baby Cobra, Ali Wong returns.")
