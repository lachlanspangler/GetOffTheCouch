"""iCalendar (.ics) feeds — the most common keyless calendar format (parks, libraries, venues, clubs).

Recurring events (RRULE) are expanded inside the horizon; at most ``max_occurrences`` per series are kept so
a weekly run club doesn't flood the feed. Conditional GET (ETag/Last-Modified) makes polling cheap.

    params:
      url: https://example.org/calendar.ics
      horizon_days: 90
      max_occurrences: 4
      default_category: community.festival     # when classification finds nothing
      category_map: {"Volunteer": volunteer.one_off}   # ICS CATEGORIES → taxonomy id
      tags: [outdoor]
      organizer: Minneapolis Park & Recreation Board
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import icalendar
import recurring_ical_events

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register, stable_id
from gotc.adapters.common import clean_text, prices_in_text, says_free


@register
class IcsAdapter(Adapter):
    name = "ics"

    def required_params(self) -> tuple[str, ...]:
        return ("url",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        urls = ctx.params["url"] if isinstance(ctx.params["url"], list) else [ctx.params["url"]]
        payloads = []
        for u in urls:
            r = ctx.http.get(u, respect_robots=self.respect_robots)
            if b"BEGIN:VCALENDAR" not in r.content[:2000]:
                raise ValueError(f"{u} did not return an iCalendar document (layout/format changed?)")
            payloads.append(Payload.from_response(r, ctx.now, "ics"))
        return FetchResult(payloads, complete=True)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        p = ctx.params
        tz = ZoneInfo(ctx.city.timezone)
        cal = icalendar.Calendar.from_ical(payload.content)
        start_window = ctx.fetched_at.astimezone(tz) - timedelta(hours=6)
        end_window = start_window + timedelta(days=int(p.get("horizon_days", 90)))
        max_occ = int(p.get("max_occurrences", 4))
        per_uid: dict[str, int] = defaultdict(int)
        cmap: dict[str, str] = p.get("category_map", {})
        occurrences = recurring_ical_events.of(cal).between(start_window, end_window)
        occurrences = sorted(occurrences, key=lambda e: _as_dt(e.get("DTSTART").dt, tz))
        for ev in occurrences:
            uid = str(ev.get("UID") or "")
            if per_uid[uid] >= max_occ:
                continue
            title = clean_text(ev.get("SUMMARY"), 300)
            if not title:
                yield {"_reject": "VEVENT without SUMMARY", "_hint": uid}
                continue
            dtstart = ev.get("DTSTART").dt
            all_day = isinstance(dtstart, date) and not isinstance(dtstart, datetime)
            start = _as_dt(dtstart, tz)
            dtend = ev.get("DTEND")
            end = _as_dt(dtend.dt, tz) if dtend else None
            if all_day and end is not None:
                end = end - timedelta(seconds=1)  # DTEND is exclusive for all-day events
            per_uid[uid] += 1
            desc = clean_text(ev.get("DESCRIPTION"), 4000)
            location = clean_text(ev.get("LOCATION"), 300)
            cats = _categories(ev)
            category = next((cmap[c] for c in cats if c in cmap), None)
            if not category:
                category = ctx.tax.classify(
                    title, " ".join(cats), desc, default=p.get("default_category", "other.uncategorized")
                ).category
            geo = ev.get("GEO")
            lat = float(geo.latitude) if geo else None
            lon = float(geo.longitude) if geo else None
            status = str(ev.get("STATUS") or "").upper()
            prices = prices_in_text(desc)
            free = says_free(title, desc)
            rrule = ev.get("RRULE")
            rid = f"{stable_id(uid or title)}:{start.isoformat()}"
            yield ctx.base(
                rid,
                title=title,
                description=desc,
                url=_url(ev.get("URL")) or p.get("default_url"),
                kind="recurring" if rrule or per_uid[uid] > 1 else p.get("kind", "one_off"),
                category=category,
                source_categories=cats,
                tags=list(p.get("tags", [])),
                start=start,
                end=end if end and end >= start else None,
                all_day=all_day,
                recurrence=_describe_rrule(rrule, start) if rrule else None,
                location={
                    "venue_name": location.split(",")[0] if location else None,
                    "address": location,
                    "lat": lat,
                    "lon": lon,
                    "geocode_method": "reported" if lat is not None else None,
                },
                organizer=p.get("organizer") or clean_text(_cn(ev.get("ORGANIZER"))),
                price={"is_free": True}
                if free and not prices
                else ({"min": min(prices), "max": max(prices)} if prices else {}),
                availability="cancelled" if status == "CANCELLED" else ("free_no_ticket" if free else "unknown"),
                _html=str(ev.get("X-ALT-DESC") or ev.get("DESCRIPTION") or ""),
            )


def _as_dt(value: date | datetime, tz: ZoneInfo) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=tz)
    return datetime(value.year, value.month, value.day, tzinfo=tz)


def _categories(ev: Any) -> list[str]:
    raw = ev.get("CATEGORIES")
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else [raw]
    out: list[str] = []
    for item in items:
        cats = getattr(item, "cats", None)
        out.extend(str(c) for c in (cats if cats is not None else [item]))
    return [c.strip() for c in out if str(c).strip()]


def _url(v: Any) -> str | None:
    s = str(v).strip() if v else ""
    return s if s.startswith(("http://", "https://")) else None


def _cn(v: Any) -> str | None:
    if not v:
        return None
    cn = getattr(v, "params", {}).get("CN")
    return str(cn) if cn else None


_DAYS = {"MO": "Mon", "TU": "Tue", "WE": "Wed", "TH": "Thu", "FR": "Fri", "SA": "Sat", "SU": "Sun"}


def _describe_rrule(rrule: Any, start: datetime) -> str:
    freq = (rrule.get("FREQ") or [""])[0]
    days = [_DAYS.get(str(d)[-2:], str(d)) for d in rrule.get("BYDAY", [])]
    when = start.strftime("%-I:%M %p").replace(":00 ", " ")
    if freq == "WEEKLY":
        interval = int((rrule.get("INTERVAL") or [1])[0])
        every = "Every other" if interval == 2 else "Every"
        return f"{every} {', '.join(days) or start.strftime('%a')} at {when}"
    if freq == "MONTHLY":
        return f"Monthly at {when}"
    if freq == "DAILY":
        return f"Daily at {when}"
    return f"Repeats ({str(freq).lower() or 'custom'})"
