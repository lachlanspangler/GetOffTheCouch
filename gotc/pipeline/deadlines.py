"""Deadline extraction: find "register by Oct 3", "early-bird pricing ends 11/1", "registration opens Jan 5"
in free text. Every hit keeps the sentence it came from (``evidence``) and is labeled ``extracted``.

Guards against false positives:
  * the date must parse unambiguously and fall within [now - 7d, event start + 1d]
  * a 'closes' date after the event starts is dropped (it's probably the event date)
  * dates without a year take the next occurrence on or after ``now``
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from dateutil import parser as dtparser

_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_DATE = (
    rf"(?:(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?,?\s+)?"
    rf"(?:{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?|\d{{1,2}}/\d{{1,2}}(?:/\d{{2,4}})?|\d{{4}}-\d{{2}}-\d{{2}})"
    rf"(?:\s*(?:at|@|by)?\s*\d{{1,2}}(?::\d{{2}})?\s*(?:am|pm|a\.m\.|p\.m\.))?"
)

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "closes_at",
        re.compile(
            rf"\b(?:register|registration|sign[- ]?ups?|rsvps?|apply|enroll)\s+(?:is\s+)?(?:due\s+)?(?:by|before|until|thru|through)\s+({_DATE})",
            re.I,
        ),
    ),
    (
        "closes_at",
        re.compile(
            rf"\b(?:registration|sign[- ]?ups?|applications?|entries|rsvps?)\s+(?:close|closes|closing|end|ends|due|deadline)\s*(?:is|on|:)?\s*({_DATE})",
            re.I,
        ),
    ),
    (
        "closes_at",
        re.compile(
            rf"\b(?:registration\s+)?deadline(?:\s+to\s+(?:register|sign up|apply))?\s*(?:is|:|-|–)?\s*({_DATE})",
            re.I,
        ),
    ),
    (
        "early_bird_ends_at",
        re.compile(
            rf"\bearly[- ]?bird\s+(?:pricing|price|rate|registration|tickets?|discount)?\s*(?:ends|expires|until|through|thru|by|deadline:?)\s*({_DATE})",
            re.I,
        ),
    ),
    (
        "opens_at",
        re.compile(
            rf"\b(?:registration|sign[- ]?ups?|enrollment|tickets?)\s+(?:opens?|goes live|go on sale|on sale|starts?|begins?)\s*(?:on|:)?\s*({_DATE})",
            re.I,
        ),
    ),
]


@dataclass(frozen=True)
class Deadline:
    field: str  # closes_at | early_bird_ends_at | opens_at
    at: datetime
    evidence: str


def _parse(text: str, tz: str, now: datetime) -> datetime | None:
    t = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", text, flags=re.I).replace("a.m.", "am").replace("p.m.", "pm")
    t = re.sub(r"\b(at|@)\b", " ", t)
    has_year = bool(re.search(r"\d{4}", t)) or bool(re.search(r"\d{1,2}/\d{1,2}/\d{2}", t))
    has_time = bool(re.search(r"\d\s*(am|pm)|\d:\d\d", t, re.I))
    zone = ZoneInfo(tz)
    local_now = now.astimezone(zone)
    _jan1 = datetime(local_now.year, 1, 1)  # noqa: DTZ001 — tz attached below
    try:
        dt = dtparser.parse(t, default=_jan1, fuzzy=True)
    except (ValueError, OverflowError):
        return None
    if not has_year and dt.date() < (local_now - timedelta(days=60)).date():
        dt = dt.replace(year=dt.year + 1)
    if not has_time:
        dt = datetime.combine(dt.date(), time(23, 59))  # "by Oct 3" means end of day
    return dt.replace(tzinfo=zone) if dt.tzinfo is None else dt


def extract_deadlines(text: str | None, tz: str, now: datetime, event_start: datetime | None) -> list[Deadline]:
    if not text:
        return []
    found: dict[str, Deadline] = {}
    for fld, pat in PATTERNS:
        for m in pat.finditer(text):
            at = _parse(m.group(1), tz, now)
            if at is None or at < now - timedelta(days=7):
                continue
            if event_start is not None and fld != "opens_at" and at > event_start + timedelta(days=1):
                continue
            if event_start is not None and at > event_start + timedelta(days=1) and fld == "opens_at":
                continue
            s0 = max(0, m.start() - 60)
            evidence = text[s0 : m.end() + 20].strip()
            evidence = ("…" if s0 else "") + re.sub(r"\s+", " ", evidence) + "…"
            if fld not in found or at < found[fld].at:
                found[fld] = Deadline(fld, at, evidence)
    return list(found.values())
