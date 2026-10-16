"""Enrichment: attendance estimates, ticket signals, price trends, derived tags, "good for meeting people".

Honesty rules (docs/METHODOLOGY.md):
  * every estimate is a band (low/mid/high) with a method string and the inputs used
  * numbers are rounded to 2 significant figures — "~1,200", never "1,187"
  * no signal → no estimate (or a wide, low-confidence prior that says it is a prior)
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from gotc.schema import (
    Availability,
    Estimate,
    Event,
    EventKind,
    PricePoint,
    PriceTrend,
    SocialScore,
    TicketSignal,
)
from gotc.taxonomy import Taxonomy

# Fill-rate bands by ticket availability: (low, mid, high) share of capacity.
FILL = {
    Availability.SOLD_OUT: (0.9, 0.97, 1.0),
    Availability.FEW_LEFT: (0.75, 0.88, 0.97),
    Availability.LIMITED: (0.65, 0.8, 0.95),
    Availability.ON_SALE: (0.4, 0.65, 0.88),
    Availability.NOT_YET_ON_SALE: (0.4, 0.7, 0.95),
}
DEFAULT_FILL = (0.2, 0.5, 0.85)


def sig2(x: float) -> float:
    """Round to 2 significant figures (fake precision is a lie)."""
    if x <= 0:
        return 0.0
    digits = 2 - math.floor(math.log10(abs(x))) - 1
    return float(round(x, digits))


def estimate_attendance(
    ev: Event, tax: Taxonomy, capacity: int | None, capacity_source: str | None, reported: int | None
) -> Estimate:
    cat = tax.categories[ev.category]
    if reported:
        return Estimate(
            low=sig2(reported * 0.85),
            mid=sig2(reported),
            high=sig2(reported * 1.15),
            method="attendance reported by the organizer/source (±15%)",
            inputs={"reported": reported},
            confidence=0.75,
        )
    if capacity and capacity >= 10:
        lo, mid, hi = FILL.get(ev.tickets.availability, DEFAULT_FILL)
        # outdoor/free events at big parks often have nominal "capacities": widen the band
        conf = 0.6 if ev.tickets.availability in FILL else 0.4
        return Estimate(
            low=min(sig2(capacity * lo), capacity),
            mid=min(sig2(capacity * mid), capacity),
            high=min(sig2(capacity * hi), capacity),
            method=(
                f"venue capacity {capacity:,}{' (Wikidata)' if (capacity_source or '').startswith('wikidata:') else ''}"
                f" × {int(lo * 100)}–{int(hi * 100)}% fill ({ev.tickets.availability.value.replace('_', ' ')})"
            ),
            inputs={
                "capacity": capacity,
                "capacity_source": capacity_source,
                "availability": ev.tickets.availability.value,
            },
            confidence=conf,
        )
    p10, p50, p90 = cat.attendance
    return Estimate(
        low=sig2(p10),
        mid=sig2(p50),
        high=sig2(p90),
        method=f"typical range for {cat.label.lower()} (category prior; no venue capacity known)",
        inputs={"category": ev.category},
        confidence=0.25,
    )


def ticket_signal(
    ev: Event, snapshots: list[dict[str, object]], now: datetime
) -> tuple[TicketSignal, PriceTrend | None]:
    """Derive availability / % left / selling-fast / trend from price snapshots across sellers."""
    statuses = [o.availability for o in ev.offers]
    availability = _best_availability(statuses) if statuses else ev.tickets.availability
    by_seller: dict[str, list[dict[str, object]]] = defaultdict(list)
    for s in snapshots:
        by_seller[str(s["seller"])].append(s)
    pct_left: Estimate | None = None
    selling_fast = False
    signal: str | None = None
    for seller, rows in by_seller.items():
        rows.sort(key=lambda r: str(r["observed_at"]))
        counts = [
            (datetime.fromisoformat(str(r["observed_at"])), int(str(r["listing_count"])))
            for r in rows
            if r["listing_count"] is not None
        ]
        if len(counts) >= 2:
            peak = max(c for _, c in counts)
            cur_t, cur = counts[-1]
            if peak >= 10:
                ratio = cur / peak
                pct_left = Estimate(
                    low=round(max(0.0, ratio * 60), 0),
                    mid=round(ratio * 100, 0),
                    high=round(min(100.0, ratio * 140), 0),
                    method=f"{seller} resale listings now ({cur}) vs. the most we've seen ({peak}); listings are not seats",
                    inputs={"seller": seller, "listings_now": cur, "listings_peak": peak},
                    confidence=0.35,
                )
            past = [c for t, c in counts if cur_t - t >= timedelta(hours=24) and cur_t - t <= timedelta(hours=96)]
            if past and max(past) >= 20 and cur <= 0.75 * max(past):
                selling_fast = True
                signal = f"{seller} listings down {round(100 * (1 - cur / max(past)))}% in the last few days"
    if availability == Availability.SOLD_OUT:
        pct_left = Estimate(low=0, mid=0, high=5, method="sold out on the primary seller", inputs={}, confidence=0.7)
    elif availability == Availability.FEW_LEFT:
        selling_fast = True
        signal = signal or "seller reports few tickets left"
    trend = _trend(snapshots, now)
    if trend and trend.direction == "up" and (trend.change_pct or 0) >= 20:
        selling_fast = True
        signal = signal or f"lowest price up {trend.change_pct:.0f}% in {trend.window_hours}h"
    return TicketSignal(availability=availability, pct_left=pct_left, selling_fast=selling_fast, signal=signal), trend


def _best_availability(statuses: list[Availability]) -> Availability:
    order = [
        Availability.CANCELLED,
        Availability.POSTPONED,
        Availability.ON_SALE,
        Availability.REGISTRATION_OPEN,
        Availability.LIMITED,
        Availability.FEW_LEFT,
        Availability.NOT_YET_ON_SALE,
        Availability.WAITLIST,
        Availability.FREE_NO_TICKET,
        Availability.REGISTRATION_CLOSED,
        Availability.SOLD_OUT,
        Availability.UNKNOWN,
    ]
    return min(statuses, key=order.index)


def _trend(snapshots: list[dict[str, object]], now: datetime, window_h: int = 168) -> PriceTrend | None:
    pts = [
        PricePoint(
            at=datetime.fromisoformat(str(s["observed_at"])),
            seller=str(s["seller"]),
            price_min=s["price_min"],
            price_max=s["price_max"],
            listing_count=s["listing_count"],
        )
        for s in snapshots
    ]
    pts.sort(key=lambda p: p.at)
    if not pts:
        return None
    recent = [p for p in pts if p.at >= now - timedelta(hours=window_h) and p.price_min]
    if len(recent) < 2:
        return PriceTrend(direction="unknown", points=pts[-30:])
    first, last = recent[0].price_min or 0, recent[-1].price_min or 0
    change = (last - first) / first * 100 if first else 0.0
    direction = "flat" if abs(change) < 5 else ("up" if change > 0 else "down")
    hours = int((recent[-1].at - recent[0].at).total_seconds() // 3600)
    return PriceTrend(direction=direction, change_pct=round(change, 1), window_hours=hours, points=pts[-30:])


_TXT = {
    "21+": re.compile(r"(?<!\d)(21\+|21 and over|21 & over|ages 21\b)", re.I),
    "all_ages": re.compile(r"\b(all ages|all-ages)\b", re.I),
    "beginner_friendly": re.compile(
        r"\b(beginners?|all (skill )?levels|no experience|learn to|newbies?|first[- ]timers?)\b", re.I
    ),
    "solo_friendly": re.compile(
        r"\b(come solo|free agents?|individuals welcome|meet new people|make new friends|no partner needed)\b",
        re.I,
    ),
    "dog_friendly": re.compile(r"\b(dog[- ]friendly|dogs welcome|pups?)\b", re.I),
    "lgbtq": re.compile(r"\b(lgbtq\+?|queer|pride|drag)\b", re.I),
    "sober_friendly": re.compile(r"\b(sober|alcohol[- ]free|zero[- ]proof|mocktails?)\b", re.I),
    "free_food": re.compile(
        r"\b(free (pizza|food|snacks|lunch|breakfast|dinner|refreshments|tacos|coffee|donuts|bagels)|"
        r"(pizza|food|snacks|lunch|breakfast|dinner|refreshments) (will be )?(provided|served|included)|light refreshments)\b",
        re.I,
    ),
    "accessible": re.compile(r"\b(wheelchair accessible|ada accessible|asl interpret)\b", re.I),
}


def derive_tags(ev: Event, text: str, tax: Taxonomy) -> list[str]:
    tags = set(ev.tags)
    top = tax.top(ev.category)
    if ev.price.is_free:
        tags.add("free")
    if ev.kind == EventKind.RECURRING or ev.recurrence:
        tags.add("recurring")
    if top == "outdoors" or ev.category in (
        "community.block_party",
        "community.market",
        "fitness.run_club",
        "fitness.race",
    ):
        tags.add("outdoor")
    if top == "family":
        tags.add("family_friendly")
    if ev.category in ("nightlife.opening", "food_drink.restaurant_opening"):
        tags.add("new_venue")
    for tag, pat in _TXT.items():
        if pat.search(text):
            tags.add(tag)
    if ev.registration:
        tags.add("registration_required")
        st = {s.value for s in ev.registration.signup_types}
        if "free_agent" in st or "individual" in st:
            tags.update({"free_agent", "solo_friendly"})
        if "team" in st:
            tags.add("team_signup")
        if ev.registration.early_bird_ends_at:
            tags.add("early_bird")
    if ev.tickets.selling_fast:
        tags.add("selling_fast")
    local = ev.start.astimezone(ZoneInfo(ev.timezone))
    if not ev.all_day and (local.hour >= 21 or local.hour < 3):
        tags.add("nightlife")
    return tax.valid_tags(sorted(tags))


def social_score(ev: Event, tax: Taxonomy) -> SocialScore:
    cat = tax.categories[ev.category]
    score = cat.social
    reasons = [f"{cat.label}: {_social_word(cat.social)} for meeting people"]
    if "recurring" in ev.tags:
        score += 0.08
        reasons.append("recurring — you'll see the same faces")
    if "solo_friendly" in ev.tags or "free_agent" in ev.tags:
        score += 0.1
        reasons.append("solo / free-agent friendly")
    if ev.attendance:
        mid = ev.attendance.mid
        if mid > 5000:
            score -= 0.15
            reasons.append("huge crowd — easy to stay anonymous")
        elif 10 <= mid <= 250:
            score += 0.05
            reasons.append("small enough to actually talk to people")
    if "beginner_friendly" in ev.tags:
        score += 0.04
        reasons.append("beginner friendly")
    return SocialScore(score=round(max(0.0, min(1.0, score)), 2), reasons=reasons)


def _social_word(x: float) -> str:
    return "great" if x >= 0.8 else "good" if x >= 0.6 else "okay" if x >= 0.4 else "not ideal"
