"""Parsing helpers shared by adapters: datetimes, money, text cleanup, address assembly."""

from __future__ import annotations

import html
import re
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from dateutil import parser as dtparser

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_MONEY = re.compile(r"\$\s*(\d{1,5}(?:,\d{3})*(?:\.\d{1,2})?)")


def clean_text(value: Any, limit: int | None = None) -> str | None:
    """Strip HTML, unescape entities, collapse whitespace. Returns None for empty input."""
    if value is None:
        return None
    s = str(value)
    s = re.sub(r"(?i)<\s*(br|/p|/div|/li)\s*/?>", "\n", s)
    s = html.unescape(_TAG.sub(" ", s))
    s = "\n".join(_WS.sub(" ", ln).strip() for ln in s.splitlines())
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    if not s:
        return None
    if limit and len(s) > limit:
        cut = s[: limit - 1].rsplit(" ", 1)[0]
        s = cut + "…"
    return s


def title_case_if_shouty(s: str) -> str:
    """'BLOCK PARTY ON 5TH AVE' → 'Block Party On 5th Ave' (only when the source shouts)."""
    letters = [c for c in s if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.8 and len(letters) > 4:
        # [\w'’]* keeps possessives whole: "LUCKY'S PUB" → "Lucky's Pub", not "Lucky'S Pub"
        return re.sub(r"\b(\w)([\w'’]*)", lambda m: m.group(1).upper() + m.group(2).lower(), s)
    return s


def parse_dt(value: Any, tz: str, default_time: time | None = None) -> datetime | None:
    """Parse a datetime-ish value into an aware datetime.

    * aware strings keep their offset;
    * naive strings are interpreted in the *city's* timezone (not UTC, not the machine's);
    * dates without times get ``default_time`` (or midnight).
    """
    if value is None or value == "":
        return None
    zone = ZoneInfo(tz)
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, default_time or time(0, 0))
    elif isinstance(value, int | float):
        ts = float(value) / (1000 if value > 1e11 else 1)
        return datetime.fromtimestamp(ts, tz=zone)
    else:
        try:
            dt = dtparser.parse(str(value))
        except (ValueError, OverflowError):
            return None
        if default_time and dt.time() == time(0, 0) and not re.search(r"\d:\d", str(value)):
            dt = datetime.combine(dt.date(), default_time, dt.tzinfo)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=zone)
    return dt


def combine_date_time(d: Any, t: Any, tz: str) -> datetime | None:
    """Combine a separate date field and time field ('2026-10-18' + '7:30 PM')."""
    base = parse_dt(d, tz)
    if base is None:
        return None
    if not t:
        return base
    try:
        tt = dtparser.parse(str(t)).time()
    except (ValueError, OverflowError):
        return base
    return base.replace(hour=tt.hour, minute=tt.minute, second=0)


def money(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        return float(value) if value >= 0 else None
    m = _MONEY.search(str(value)) or re.search(r"(\d+(?:\.\d{1,2})?)", str(value))
    return float(m.group(1).replace(",", "")) if m else None


def prices_in_text(text: str | None) -> list[float]:
    if not text:
        return []
    return [float(m.replace(",", "")) for m in _MONEY.findall(text)]


_FREE = re.compile(
    r"(^\s*free\b(?! parking| drinks?| food| shuttle| wi-?fi| t-?shirt| swag)"
    r"|\bfree (admission|entry|event|to attend|to join|to play|to participate|and open|of charge|for all|for everyone)\b"
    r"|\b(admission|entry|it|event|this event|participation) (is|are) (always )?free\b"
    r"|\bno (cover|charge|cost|fee)\b)",
    re.I | re.M,
)


def says_free(*texts: str | None) -> bool:
    """True only on explicit free-admission language. 'gluten free' / 'free parking' don't count."""
    hay = "\n".join(t for t in texts if t)
    if not hay:
        return False
    if re.search(r"\$\s*[1-9]", hay):
        return False
    return bool(_FREE.search(hay))


def join_address(*parts: Any) -> str | None:
    out = [str(p).strip() for p in parts if p and str(p).strip()]
    return ", ".join(dict.fromkeys(out)) or None


def end_or_default(start: datetime, end: datetime | None, hours: float = 2.0) -> datetime | None:
    if end is None or end < start:
        return None
    if end - start > timedelta(days=120):  # "season" records with absurd spans: keep, the UI shows a range
        return end
    return end


def infer_year(month: int, day: int, ref: date, weekday: int | None = None, grace_days: int = 60) -> date | None:
    """Resolve a year-less "M/D" to a full date. Rule (documented in METHODOLOGY via the adapters using it):

    * the **next occurrence on or after ``ref``** (the fetch date in the city's timezone);
    * if the source also shows a weekday (``weekday``: Mon=0) and that rule's date falls on a different
      weekday, but this year's already-passed date (within ``grace_days``) matches, take the past date —
      e.g. a league that started last week and still lists its first game.
    Returns None for impossible dates (2/30).
    """
    cands: list[date] = []
    for y in (ref.year - 1, ref.year, ref.year + 1):
        try:
            cands.append(date(y, month, day))
        except ValueError:
            continue
    if not cands:
        return None
    nxt = next((d for d in cands if d >= ref), None)
    if weekday is not None and (nxt is None or nxt.weekday() != weekday):
        recent = [d for d in cands if d < ref and (ref - d).days <= grace_days and d.weekday() == weekday]
        if recent:
            return recent[-1]
        later = [d for d in cands if d >= ref and d.weekday() == weekday]
        if later:
            return later[0]
    return nxt


def weekly_occurrences(weekday: int, at: str, tz: str, now: datetime, n: int = 4) -> list[datetime]:
    """The next ``n`` dates of a weekly schedule ("Wednesdays 7:00 PM": weekday=2, at='7:00 PM') in the city's
    zone, starting today if the time hasn't passed yet. Wall-clock time is kept across DST changes."""
    t = dtparser.parse(at).time()
    zone = ZoneInfo(tz)
    local_now = now.astimezone(zone)
    first = local_now.date() + timedelta(days=(weekday - local_now.weekday()) % 7)
    if datetime.combine(first, t, zone) <= local_now:
        first += timedelta(days=7)
    return [datetime.combine(first + timedelta(weeks=i), t, zone) for i in range(n)]


US_STATES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts",
    "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}  # fmt: skip
_STATE_BY_NAME = {v.lower(): k for k, v in US_STATES.items()}


def us_state_code(value: str | None) -> str | None:
    """'MN' / 'Minnesota' / 'minnesota' → 'MN'; anything else (UK, Ontario, USA) → None."""
    if not value:
        return None
    v = value.strip().rstrip(".")
    if v.upper() in US_STATES:
        return v.upper()
    return _STATE_BY_NAME.get(v.lower())


def dig(obj: Any, path: str, default: Any = None) -> Any:
    """dig(d, 'a.b.0.c') — tolerant nested lookup used by config-driven field mappings."""
    cur = obj
    for part in path.split("."):
        if cur is None:
            return default
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return default
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return default
    return default if cur is None else cur
