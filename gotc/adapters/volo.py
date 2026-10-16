"""Volo Sports league discovery pages (server-rendered HTML, keyless).

    GET https://www.volosports.com/discover/<city-slug>?category=leagues[&page=N][&includeFees=true]

robots.txt allows everything except /rfo /admin /staff (re-checked live 2026-10-16); the ToS grants a personal-use
licence with no scraping/robot clause (research 2026-10-15). We fetch at most ``max_pages`` pages a day, ≥3 s apart,
keep facts only (title, dates, price, deadline) and always link back to the program page.

Gotchas (all handled here):
  * **Dates have no year** ("11/8", "Closes 11/6", "Price goes up 10/17"). We take the *next occurrence on or after
    the fetch date in the city's timezone*; for the first game date we also check the weekday the card shows and
    accept a date up to 60 days in the past if only that one matches (a season that already started).
    See ``gotc.adapters.common.infer_year``.
  * "Closing in 2h 19m" is relative to the server's clock → ``fetched_at + delta`` (method: extracted).
  * "Price goes up 10/17" → early-bird ends at the start of 10/17, local time.
  * Some cities (Boston, LA) 307-redirect to add ``includeFees=true`` (prices then include fees). Configure
    ``include_fees: true`` for those so the redirect doesn't drop ``page=N``; ``page=1`` must be omitted.
  * Pagination is client-side links; the server honours ``page=N`` only without cookies (PoliteClient never
    stores cookies). "N ways to play" gives the total, which decides whether the snapshot is complete.

    params:
      city_slug: boston               # from https://www.volosports.com/sitemap.xml
      include_fees: true              # Boston, LA
      max_pages: 6
"""

from __future__ import annotations

import html as htmllib
import math
import re
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text, infer_year

BASE = "https://www.volosports.com"
PAGE_SIZE = 24
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_CARD_LINK = re.compile(rf'href="/l/({_UUID})"')
_TOTAL = re.compile(r"<span>(\d+)</span>\s*<span>ways to play</span>")
_SPAN = re.compile(r'<span(?:\s+class="([^"]*)")?[^>]*>([^<]*)</span>')
_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_DAY_RE = r"(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day"
_DAY_SEG = re.compile(rf"^{_DAY_RE}(?:\s*(?:,|&|/|and)\s*{_DAY_RE})*$", re.I)
_MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
_SEASON = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})$"
)
_SCHEDULE = re.compile(
    r"^(\d{1,2})/(\d{1,2})\s*·\s*(?:(\d+)\s*weeks?)?\s*(?:·\s*)?"
    r"(\d{1,2}(?::\d{2})?\s*[AP]M)?\s*(?:-\s*(\d{1,2}(?::\d{2})?\s*[AP]M))?",
    re.I,
)
_CLOSES = re.compile(r"\bCloses\s+(?:on\s+)?(?:tomorrow\s+|today\s+)?(\d{1,2})/(\d{1,2})\b", re.I)
_TOMORROW = re.compile(r"^\s*(?:Closes\s+)?(?:Tomorrow|Today)\s+(\d{1,2})/(\d{1,2})\b", re.I)
_CLOSING_IN = re.compile(r"\bClosing in\s+(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?", re.I)
_PRICE_UP = re.compile(r"Price goes up\s+(\d{1,2})/(\d{1,2})", re.I)
_SPOTS = re.compile(r"(\d+)\s+TEAM\s+SPOTS?\s+(?:LEFT|REMAINING)", re.I)

# order matters: the first keyword found wins ("flag football" before "football", "beach volleyball" → volleyball)
SPORTS: list[tuple[str, str, str]] = [
    ("flag football", "flag_football", "Flag Football"),
    ("kickball", "kickball", "Kickball"),
    ("softball", "softball", "Softball"),
    ("pickleball", "pickleball", "Pickleball"),
    ("volleyball", "volleyball", "Volleyball"),
    ("bowling", "bowling", "Bowling"),
    ("basketball", "basketball", "Basketball"),
    ("dodgeball", "dodgeball", "Dodgeball"),
    ("skee-ball", "cornhole", "Skee-Ball"),
    ("skeeball", "cornhole", "Skee-Ball"),
    ("cornhole", "cornhole", "Cornhole"),
    ("ultimate", "ultimate", "Ultimate"),
    ("futsal", "soccer", "Futsal"),
    ("soccer", "soccer", "Soccer"),
]

_SKILL_BADGES = {
    "all skills": ["all"],
    "social/beginner": ["beginner"],
    "beginner": ["beginner"],
    "social": ["beginner"],
    "recreational": ["recreational"],
    "rec": ["recreational"],
    "intermediate": ["intermediate"],
    "competitive": ["competitive"],
    "advanced": ["competitive"],
}
_SKILL_TOKENS = [
    (re.compile(r"\bbeginners?\b", re.I), "beginner"),
    (re.compile(r"\brec(?:reational)?\b", re.I), "recreational"),
    (re.compile(r"\bint(?:ermediate)?\b", re.I), "intermediate"),
    (re.compile(r"\b(?:comp(?:etitive)?|advanced)\b", re.I), "competitive"),
]
_PRICE_LABELS = ("early bird", "last chance", "regular", "standard")
_KNOWN_BADGES = re.compile(r"^(League|Pickup|Drop-?in|Tournament|Clinic|Class|Indoor|Outdoor|Turf|STAFF PICK)$", re.I)


@register
class VoloAdapter(Adapter):
    name = "volo"

    def required_params(self) -> tuple[str, ...]:
        return ("city_slug",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        base = str(p.get("base_url", BASE)).rstrip("/")
        url = f"{base}/discover/{p['city_slug']}"
        max_pages = int(p.get("max_pages", 6))
        payloads: list[Payload] = []
        seen: set[str] = set()
        total: int | None = None
        last_short = False
        for page in range(1, max_pages + 1):
            q: dict[str, str | int] = {"category": str(p.get("category", "leagues"))}
            if page > 1:
                q["page"] = page
            if p.get("include_fees"):
                q["includeFees"] = "true"
            r = ctx.http.get(url, params=q)
            text = r.text
            if 'id="results-grid"' not in text and "ways to play" not in text:
                raise ValueError(f"{url}: no results grid — Volo page layout changed?")
            if total is None and (m := _TOTAL.search(text)):
                total = int(m.group(1))
            ids = set(_CARD_LINK.findall(text))
            got_page = int((parse_qs(urlsplit(r.url).query).get("page") or ["1"])[0])
            if page > 1 and (got_page != page or not ids - seen):
                break  # redirected away from ?page=N, or nothing new: stop rather than store duplicates
            payloads.append(Payload.from_response(r, ctx.now, "html", page=page))
            seen |= ids
            last_short = len(ids) < PAGE_SIZE
            if last_short or (total is not None and page >= math.ceil(total / PAGE_SIZE)):
                break
        complete = (len(seen) >= total) if total is not None else last_short
        return FetchResult(payloads, complete=complete)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        text = payload.text
        tz = ZoneInfo(ctx.city.timezone)
        ref = ctx.fetched_at.astimezone(tz).date()
        fees = "includefees=true" in payload.url.lower()
        base = f"{urlsplit(payload.url).scheme}://{urlsplit(payload.url).netloc}"
        for chunk in text.split('data-slot="card"')[1:]:
            m = _CARD_LINK.search(chunk)
            if not m:
                continue  # promo tiles (Volo Pass) are not programs
            yield _card(chunk, m.group(1), ctx, tz, ref, fees, base, payload.url)


def _card(
    chunk: str, uuid: str, ctx: ParseContext, tz: ZoneInfo, ref: date, fees: bool, base: str, page_url: str
) -> dict[str, Any]:
    h4 = re.search(r"<h4[^>]*>(.*?)</h4>", chunk, re.S)
    raw_title = clean_text(h4.group(1)) if h4 else None
    if not raw_title:
        return {"_reject": "card without title", "_hint": uuid}
    head, body = chunk[: h4.start()] if h4 else "", chunk[h4.end() :] if h4 else chunk
    head_texts = [t for _, t in _spans(head)]
    body_spans = _spans(body)
    body_texts = [t for _, t in body_spans]

    sched_i = next((i for i, t in enumerate(body_texts) if _SCHEDULE.match(t)), None)
    sm = _SCHEDULE.match(body_texts[sched_i]) if sched_i is not None else None
    if sm is None or sched_i is None:
        return {"_reject": "no first-game date on card", "_hint": f"{uuid}: {raw_title}"}
    month, day, weeks, t_start, t_end = sm.groups()

    days, program, hood, season = _split_title(raw_title)
    if not days:
        days = [t for t in head_texts if t in _DAYS]
    year_stated = season is not None and season[0] == int(month)
    if year_stated and season is not None:
        try:
            first: date | None = date(season[1], int(month), int(day))
        except ValueError:
            first = None
    else:
        first = infer_year(int(month), int(day), ref, _DAYS.index(days[0]) if days else None)
    if first is None:
        return {"_reject": f"impossible date {month}/{day}", "_hint": uuid}
    start_t, end_t = _clock(t_start), _clock(t_end)
    start = datetime.combine(first, start_t or time(0, 0), tz)
    end = datetime.combine(first, end_t, tz) if end_t else None
    if end is not None and end < start:
        end += timedelta(days=1)

    venue_m = re.search(r'aria-label="Show venue on map"[^>]*>\s*<span[^>]*>([^<]+)</span>', body)
    venue = clean_text(venue_m.group(1)) if venue_m else None
    footer = [t for c, t in body_spans if "hidden" in c.split() and "xs:block" in c.split()]
    gender, skill_badge, team_size = ([*footer, None, None, None])[:3]
    after_price = body_texts[sched_i + 1 :]
    player, team, tier = _prices(body_spans[sched_i + 1 :])

    program_type = head_texts[0] if head_texts else None
    statuses = [t for t in head_texts + after_price if _is_status(t)]
    promo = [
        t
        for t in head_texts[1:]
        if t not in _DAYS and not _is_status(t) and not _KNOWN_BADGES.match(t) and not _PRICE_UP.search(t)
    ]
    all_text = " ".join([raw_title, *head_texts, *body_texts])

    sport_id, sport_label = _sport(f"{program} {raw_title}")
    title = f"Volo {program}" + (f" — {hood}" if hood else "") + (f" ({'/'.join(d[:3] for d in days)})" if days else "")

    closes, close_ev = _closes(statuses, ref, tz, ctx.fetched_at)
    early = None
    for t in head_texts:
        if pm := _PRICE_UP.search(t):
            d = infer_year(int(pm.group(1)), int(pm.group(2)), ref)
            early = datetime.combine(d, time(0, 0), tz) if d else None
            close_ev.append(t.replace("🏷️", "").strip())
    # deadlines belong to *this* season: a year-less deadline that lands after the first game is last year's date
    closes, early = _not_after(closes, start), _not_after(early, start)
    url = f"{base}/l/{uuid}"

    avail = "registration_open"
    spots = None
    if any("sold out" in s.lower() for s in statuses):
        avail = "sold_out"
    elif sm2 := next((_SPOTS.search(s) for s in statuses if _SPOTS.search(s)), None):
        spots = int(sm2.group(1))
        avail = "few_left" if spots <= 2 else "limited"
    elif tier == "last chance":
        avail = "few_left"
    if closes is not None and closes < ctx.fetched_at:
        avail = "registration_closed"

    signup: list[str] = []
    if player:
        signup.append("individual")
    if team:
        signup.append("team")
    if re.search(r"free agents?|FA'?s\b", all_text, re.I):
        signup.append("free_agent")
    skills = _skills(skill_badge, f"{program} {raw_title}")

    tags: list[str] = []
    if re.search(r"(?<![\w$])21\+", all_text):
        tags.append("21+")
    if "Indoor" in head_texts or re.search(r"\bindoor\b", raw_title, re.I):
        tags.append("indoor")
    if re.search(r"\boutdoor\b", raw_title, re.I):
        tags.append("outdoor")
    if tier == "early bird" or early:
        tags.append("early_bird")
    if team:
        tags.append("team_signup")
    if "free_agent" in signup:
        tags.append("free_agent")
    if "beginner" in skills:
        tags.append("beginner_friendly")

    price: dict[str, Any] = {}
    if player:
        note = "per player"
        if team:
            note += f"; {_fmt(min(team))}/team"
        if fees:
            note += "; incl. fees"
        price = {"min": min(player), "max": max(player), "note": note}
    elif team:
        price = {"min": min(team), "max": max(team), "note": "per team" + ("; incl. fees" if fees else "")}

    registration: dict[str, Any] = {
        "closes_at": closes,
        "early_bird_ends_at": early,
        "signup_types": signup,
        "skill_levels": skills,
        "url": url,
        "evidence": " · ".join(dict.fromkeys(close_ev)) or None,
        "method": "extracted",
        "confidence": 0.85 if closes or early else 0.9,
    }
    offer = {
        "seller": "Volo",
        "kind": "registration",
        "url": url,
        "price_min": price.get("min"),
        "price_max": price.get("max"),
        "listing_count": None,
        "availability": avail,
        "fees_included": True if fees else None,
        "source_id": ctx.source.id,
        "fetched_at": ctx.fetched_at,
    }
    is_league = (program_type or "").lower() == "league"
    return ctx.base(
        uuid,
        title=title[:300],
        description=" · ".join(promo) or None,
        url=url,
        kind="season" if is_league else "one_off",
        category=f"sports_league.{sport_id}",
        source_categories=[c for c in (sport_label, program_type, gender, skill_badge, team_size) if c],
        tags=tags,
        start=start,
        end=end,
        recurrence=_recurrence(days, weeks, t_start, t_end),
        location={"venue_name": venue, "neighborhood": hood},
        organizer="Volo Sports",
        price=price,
        offers=[offer],
        registration=registration,
        availability=avail,
        extras={
            "program_type": program_type,
            "volo_title": raw_title,
            "gender_format": gender,
            "team_size": team_size,
            "skill_badge": skill_badge,
            "weeks": int(weeks) if weeks else None,
            "team_price_min": min(team) if team else None,
            "team_price_max": max(team) if team else None,
            "price_tier": tier,
            "team_spots_left": spots,
            "staff_pick": any(t.upper() == "STAFF PICK" for t in head_texts) or None,
            "status_text": " · ".join(statuses) or None,
            "includes_fees": fees,
            "first_game_raw": f"{month}/{day}",
            "year_inferred": not year_stated,
            "listing_page": page_url,
        },
    )


def _spans(fragment: str) -> list[tuple[str, str]]:
    frag = re.sub(r"<svg.*?</svg>", "", fragment, flags=re.S)
    out = []
    for cls, txt in _SPAN.findall(frag):
        t = clean_text(htmllib.unescape(txt))
        if t:
            out.append((cls or "", t))
    return out


def _split_title(title: str) -> tuple[list[str], str, str | None, tuple[int, int] | None]:
    """Split a Volo card title into (days, program, neighborhood, (month, year) if stated). Two layouts exist:

    'Monday, Wednesday - Beach Volleyball - Santa Monica'            → days first, neighborhood last
    'Bocce (Coed) - Thursday - The Underline - Bocce (Coconut Grove) - November 2026'  (Miami)
                                                                     → program, days, venue (neighborhood), season
    """
    segs = [s.strip() for s in re.split(r"\s*-\s+|\s+-\s*", title) if s.strip()]
    season: tuple[int, int] | None = None
    if segs and (sm := _SEASON.match(segs[-1])):
        season = (_MONTHS.index(sm.group(1).lower()[:3]) + 1, int(sm.group(2)))
        segs = segs[:-1]
    day_i = next((i for i, s in enumerate(segs) if _DAY_SEG.match(s)), None)
    days = [d.capitalize() for d in re.findall(_DAY_RE, segs[day_i], re.I)] if day_i is not None else []
    if day_i is not None and day_i > 0:  # program first, then days, then "Venue (Neighborhood)"
        program = " - ".join(segs[:day_i])
        tail = segs[day_i + 1 :]
        pm = re.search(r"\(([^()]+)\)\s*$", tail[-1]) if tail else None
        return days, program, (pm.group(1).strip() if pm else (tail[-1] if tail else None)), season
    rest = segs[day_i + 1 :] if day_i == 0 else segs
    if len(rest) >= 2:
        return days, " - ".join(rest[:-1]), rest[-1], season
    return days, (rest[0] if rest else title), None, season


def _clock(s: str | None) -> time | None:
    if not s:
        return None
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*([AP])M", s.strip(), re.I)
    if not m:
        return None
    h = int(m.group(1)) % 12 + (12 if m.group(3).upper() == "P" else 0)
    return time(h, int(m.group(2) or 0))


def _prices(spans: list[tuple[str, str]]) -> tuple[list[float], list[float], str | None]:
    """Walk the price line: [label] [$struck regular] $current /player · [$struck] $current /team."""
    player: list[float] = []
    team: list[float] = []
    tier: str | None = None
    bucket: list[float] = []
    for _cls, t in spans:
        low = t.lower()
        if low in _PRICE_LABELS and tier is None:
            tier = low
        elif re.fullmatch(r"\$[\d,]+(?:\.\d{1,2})?", t):
            bucket.append(float(t[1:].replace(",", "")))
        elif low == "/player":
            player, bucket = bucket, []
        elif low == "/team":
            team, bucket = bucket, []
            break
        elif bucket and not t.startswith("·"):
            break
    return player, team, tier


def _is_status(t: str) -> bool:
    return bool(re.search(r"\bclos(es|ing)\b|sold out|spots? (left|remaining)|^tomorrow\b|^today\b|waitlist", t, re.I))


def _closes(statuses: list[str], ref: date, tz: ZoneInfo, fetched_at: datetime) -> tuple[datetime | None, list[str]]:
    for s in statuses:
        if m := (_CLOSES.search(s) or _TOMORROW.match(s)):
            d = infer_year(int(m.group(1)), int(m.group(2)), ref)
            if d:
                return datetime.combine(d, time(23, 59), tz), [s]
        if (m2 := _CLOSING_IN.search(s)) and any(m2.groups()):
            dd, hh, mm = (int(x or 0) for x in m2.groups())
            return fetched_at + timedelta(days=dd, hours=hh, minutes=mm), [s]
    return None, []


def _not_after(dt: datetime | None, start: datetime) -> datetime | None:
    if dt is None or dt <= start + timedelta(days=1):
        return dt
    try:
        prev = dt.replace(year=dt.year - 1)
    except ValueError:  # 2/29
        return dt
    return prev if prev <= start else dt


def _sport(text: str) -> tuple[str, str | None]:
    low = text.lower()
    for kw, sid, label in SPORTS:
        if kw in low:
            return sid, label
    return "other", None


def _skills(badge: str | None, title: str) -> list[str]:
    if not badge:
        return []
    b = badge.strip().lower()
    if b in _SKILL_BADGES:
        return _SKILL_BADGES[b]
    if m := re.fullmatch(r"skills \((\d+)\)", b):
        # the card only says how many levels; take them from the title, and only if the counts agree
        found = list(dict.fromkeys(level for pat, level in _SKILL_TOKENS if pat.search(title)))
        return found if found and len(found) <= int(m.group(1)) else []
    return []


def _fmt(v: float) -> str:
    return f"${v:,.2f}".replace(".00", "")


def _recurrence(days: list[str], weeks: str | None, t_start: str | None, t_end: str | None) -> str | None:
    parts = []
    if days:
        parts.append(" & ".join(f"{d}s" for d in days))
    if weeks:
        parts.append(f"{weeks} weeks")
    if t_start:
        parts.append(_range(t_start, t_end))
    return " · ".join(parts) or None


def _range(a: str, b: str | None) -> str:
    def norm(s: str) -> tuple[str, str]:
        m = re.match(r"(\d{1,2}(?::\d{2})?)\s*([AP]M)", s.strip(), re.I)
        return (m.group(1), m.group(2).upper()) if m else (s, "")

    ta, ma = norm(a)
    if not b:
        return f"{ta} {ma}".strip()
    tb, mb = norm(b)
    return f"{ta}–{tb} {mb}" if ma == mb else f"{ta} {ma}–{tb} {mb}"
