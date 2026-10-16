"""Ranking hints: profile-independent signals precomputed for the browser ranker (RANKING.md §4, §5.1).

The card feed drops full descriptions and provenance, and the browser has no run history, so the
signals that need them are computed here, once per export:

  fp        near-duplicate fingerprint (normalized title | venue or ~300 m geocell | local date);
            same-day, same-place titles with char-3-gram Jaccard ≥ 0.8 share one fp
  group     multi-site group: the same program (title + organizer) on the same local day at 2+ venues
  desc_len  length of the full description
  flags     administrative / low-information flags; ``lowq`` is their weighted sum, capped at 1
  complete  share of 7 key fields present; ``quality = complete × (1 − lowq)``
  src_rel   the best member source unit's 30-day reliability (gotc.health.reliability), 0–1

Everything here is pure: (events, reliability scores, now) → events with ``rank`` set.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from gotc.schema import Event, EventKind, RankHints

# Administrative noise in library / park / campus calendars (RANKING.md §4). Checked against real feeds
# on 2026-10-16: "Committee" alone hit a charity benefit dinner, so only meeting-ish committee phrases count.
ADMIN = re.compile(
    r"\b(closed|closure|rentals?|reserved|private (event|party)|staff only|members only|board meeting|"
    r"(advisory )?committee (meeting|session)|advisory committee|office hours|study rooms?|test event)\b",
    re.I,
)
CANCELLED_TITLE = re.compile(r"^\W*(cancell?ed|postponed)\b", re.I)
PROMO = re.compile(r"\b(use code|\d+% off|promo( code)?|limited time offer|buy now)\b", re.I)
GENERIC = {"event", "events", "meeting", "program", "programs", "open play", "tbd", "tba", "class", "activity"}
GENERIC_VENUE = re.compile(
    r"^(usa|united states|us|online|virtual|tbd|tba|various( locations)?|see (website|details))$", re.I
)
ONLINE = re.compile(r"\b(online|virtual|zoom|webinar|livestream)\b", re.I)
EMOJI_RUN = re.compile(r"[☀-➿\U0001F300-\U0001FAFF★☆✨]{3,}")
# daily-ish is normal here; volunteer shifts added 2026-10-16 (food-pantry shifts are habits, not noise)
HABIT_FAMILIES = {"trivia_games", "fitness", "sports_league", "volunteer"}

WEIGHTS = {
    "admin": 1.0,
    "cancelled_title": 1.0,
    "generic_title": 0.4,
    "all_caps": 0.2,
    "shouty": 0.2,
    "no_info": 0.3,
    "no_place": 0.4,
    "promo": 0.3,
    "long_span": 0.3,
    "noise_recurring": 0.6,
}
HARD_NOISE = "hard_noise"  # ≥ 2 admin phrases, or a cancelled title: the browser drops these outright


def norm_title(title: str) -> str:
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", t)  # "(ages 6-12)", "[TEENS]"
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def trigrams(s: str) -> set[str]:
    s = f"  {s} "
    return {s[i : i + 3] for i in range(len(s) - 2)}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a or b else 1.0


def _local_date(e: Event) -> str:
    return e.start.astimezone(ZoneInfo(e.timezone)).date().isoformat()


def _place_key(e: Event) -> str:
    if e.venue_id:
        return e.venue_id
    if e.location.lat is not None and e.location.lon is not None:
        return f"{round(e.location.lat / 0.003)}:{round(e.location.lon / 0.003)}"  # ~300 m cell
    return norm_title(e.location.venue_name or "") or "-"


def fingerprint(e: Event) -> str:
    raw = f"{norm_title(e.title)}|{_place_key(e)}|{_local_date(e)}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def real_venue(e: Event) -> bool:
    v = (e.location.venue_name or "").strip()
    return bool(v) and not GENERIC_VENUE.match(v)


def price_known(e: Event) -> bool:
    return e.price.is_free or e.price.min is not None


def completeness(e: Event, desc_len: int) -> float:
    bits = [
        real_venue(e),
        e.location.lat is not None,
        price_known(e),
        e.url is not None,
        e.end is not None,
        desc_len >= 80,
        not e.category.startswith("other."),
    ]
    return round(sum(bits) / len(bits), 2)


def quality_flags(e: Event, desc_len: int, series_30d: int) -> list[str]:
    title = e.title.strip()
    flags: list[str] = []
    admin_hits = {m.group(0).lower() for m in ADMIN.finditer(title)}
    if admin_hits:
        flags.append("admin")
    if CANCELLED_TITLE.search(title):
        flags.append("cancelled_title")
    if len(admin_hits) >= 2 or "cancelled_title" in flags:
        flags.append(HARD_NOISE)
    nt = norm_title(title)
    if len(nt.split()) <= 2 and nt in GENERIC:
        flags.append("generic_title")
    letters = [c for c in title if c.isalpha()]
    if len(title) > 12 and letters and sum(c.isupper() for c in letters) / len(letters) > 0.6:
        flags.append("all_caps")
    if title.count("!") >= 3 or EMOJI_RUN.search(title):
        flags.append("shouty")
    if desc_len == 0 and not price_known(e) and e.url is None:
        flags.append("no_info")
    online = ONLINE.search(f"{title} {e.location.venue_name or ''}")
    if not (e.location.venue_name or "").strip() and e.location.lat is None and not online:
        flags.append("no_place")
    if PROMO.search(title):
        flags.append("promo")
    if e.end is not None and e.end - e.start > timedelta(days=3) and e.kind != EventKind.SEASON:
        exhibit = e.category in ("arts.museum",) and real_venue(e)
        if not exhibit:
            flags.append("long_span")
    if series_30d > 12 and e.category.split(".")[0] not in HABIT_FAMILIES:
        flags.append("noise_recurring")
    return flags


def low_quality(flags: list[str]) -> float:
    return round(min(1.0, sum(WEIGHTS.get(f, 0.0) for f in flags)), 2)


def _series_counts(events: list[Event], now: datetime) -> dict[str, int]:
    horizon = now + timedelta(days=30)
    out: dict[str, int] = defaultdict(int)
    for e in events:
        if e.series_id and now - timedelta(hours=3) <= e.start <= horizon:
            out[e.series_id] += 1
    return out


def _near_dup_fps(events: list[Event]) -> dict[str, str]:
    """Event id → fingerprint, with near-duplicates (same day + place, title 3-gram Jaccard ≥ 0.8) merged."""
    fps = {e.id: fingerprint(e) for e in events}
    blocks: dict[tuple[str, str], list[Event]] = defaultdict(list)
    for e in events:
        blocks[(_local_date(e), _place_key(e))].append(e)
    for members in blocks.values():
        if len(members) < 2:
            continue
        grams = [(m, trigrams(norm_title(m.title))) for m in members]
        for i, (a, ga) in enumerate(grams):
            for b, gb in grams[i + 1 :]:
                if fps[a.id] != fps[b.id] and jaccard(ga, gb) >= 0.8:
                    keep, drop = sorted((fps[a.id], fps[b.id]))
                    for k, v in fps.items():
                        if v == drop:
                            fps[k] = keep
    return fps


def _groups(events: list[Event]) -> dict[str, tuple[str, int]]:
    """Event id → (group id, venues) for programs running at 2+ venues on the same local day."""
    by_key: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        key = f"{norm_title(e.title)}|{(e.organizer or '').strip().lower()}|{_local_date(e)}"
        by_key[key].append(e)
    out: dict[str, tuple[str, int]] = {}
    for key, members in by_key.items():
        venues = {_place_key(m) for m in members}
        if len(venues) < 2:
            continue
        gid = "g_" + hashlib.sha1(key.encode()).hexdigest()[:10]
        for m in members:
            out[m.id] = (gid, len(venues))
    return out


def best_reliability(e: Event, scores: Mapping[str, float | None]) -> float | None:
    vals = [s for ref in e.sources if (s := scores.get(ref.source_id)) is not None]
    return round(max(vals) / 100, 2) if vals else None


def annotate(events: list[Event], scores: Mapping[str, float | None], now: datetime) -> list[Event]:
    """Return copies of ``events`` with ``rank`` hints set. ``scores``: source_id → reliability 0–100."""
    series = _series_counts(events, now)
    fps = _near_dup_fps(events)
    groups = _groups(events)
    out = []
    for e in events:
        desc_len = len(e.summary or "")
        flags = quality_flags(e, desc_len, series.get(e.series_id or "", 0))
        lowq = low_quality(flags)
        comp = completeness(e, desc_len)
        gid, gn = groups.get(e.id, (None, 1))
        hints = RankHints(
            fp=fps[e.id],
            group=gid,
            group_n=gn,
            desc_len=desc_len,
            flags=flags,
            lowq=lowq,
            complete=comp,
            quality=round(comp * (1 - lowq), 2),
            src_rel=best_reliability(e, scores),
        )
        out.append(e.model_copy(update={"rank": hints}))
    return out
