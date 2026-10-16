"""Trumba calendar JSON feeds (Seattle Public Library, University of Washington, many universities/cities).

Feed: ``https://www.trumba.com/calendars/<webname>.json?startdate=YYYYMMDD&days=N`` (also ``.ics``/``.rss``).
Keyless, public, published for embedding; trumba.com robots.txt allows everything. Always pass
``startdate``/``days``: an unfiltered feed returns the whole calendar (> 1 MB).

Times are local wall-clock (``startDateTime``, no offset) plus ``startTimeZoneOffset`` ("-0700"); we use
the explicit offset. Locations are HTML anchors; UW's link to Google Maps with ``q=lat,lon``. Free-form
``customFields`` carry event types, rooms and registration notes.

    params:
      webname: kalendaro
      horizon_days: 21
      organizer: Seattle Public Library
      category_fields: [Event Types]            # customFields whose values are category labels
      category_map: {Exhibits: arts.museum}
      default_category: arts.books
      venue_label: Seattle Public Library       # venue_name = "<label> – <location>"
      include_virtual: false
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text, parse_dt, says_free
from gotc.adapters.mapped import sane_coords

_MAPS = re.compile(r"maps[^\"']*[?&]q=(-?\d{1,3}\.\d+),\s*(-?\d{1,3}\.\d+)")
_HREF = re.compile(r"""href\s*=\s*["'](https?://[^"']+)["']""", re.I)
_OFFSET = re.compile(r"^[+-]\d{4}$")
_VIRTUAL = re.compile(r"(?i)\b(online|virtual|zoom|webinar|livestream)\b( only| event)?")
_CATEGORY_FIELDS = ("Event Types", "Event Type", "Event type", "Audience", "Category", "Categories")


@register
class TrumbaAdapter(Adapter):
    name = "trumba"

    def required_params(self) -> tuple[str, ...]:
        return ("webname",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        local = ctx.now.astimezone(ZoneInfo(ctx.city.timezone)).date()
        url = f"https://www.trumba.com/calendars/{p['webname']}.json"
        q: dict[str, str | int] = {"startdate": local.strftime("%Y%m%d"), "days": int(p.get("horizon_days", 21))}
        r = ctx.http.get(url, params=q)
        if not isinstance(r.json(), list):
            raise ValueError("Trumba feed did not return a JSON array — webname changed or calendar unpublished?")
        return FetchResult([Payload.from_response(r, ctx.now, "json")], complete=True)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        p = ctx.params
        data = json.loads(payload.content)
        if not isinstance(data, list):
            yield {"_reject": "payload is not a JSON array", "_hint": payload.text[:200]}
            return
        cmap: dict[str, str] = p.get("category_map", {})
        cat_fields = set(p.get("category_fields", _CATEGORY_FIELDS))
        for ev in data:
            if not isinstance(ev, dict):
                yield {"_reject": "event is not an object", "_hint": str(ev)[:200]}
                continue
            title = clean_text(ev.get("title"), 300)
            start = _when(ev.get("startDateTime"), ev.get("startTimeZoneOffset"), ctx.city.timezone)
            if not ev.get("eventID") or not title or start is None:
                yield {"_reject": "missing eventID/title/start", "_hint": json.dumps(ev)[:200]}
                continue
            virtual = _VIRTUAL.search(str(ev.get("locationType") or "")) or _VIRTUAL.fullmatch(
                (clean_text(ev.get("location")) or "").strip()
            )
            if virtual and not p.get("include_virtual", False):
                continue  # online-only: not something to get off the couch for
            custom = {
                str(c.get("label", "")): str(c.get("value", ""))
                for c in ev.get("customFields") or []
                if isinstance(c, dict)
            }
            cats = [
                x.strip()
                for label, value in custom.items()
                if label in cat_fields
                for x in (clean_text(value) or "").split(",")
                if x.strip() and x.strip().lower() != "not specified"
            ]
            desc_html = ev.get("description") or ""
            desc = clean_text(desc_html, 4000)
            category = (
                next((cmap[k] for k in cmap if k in cats), None)
                or ctx.tax.classify(
                    title, " ".join(cats), desc, default=p.get("default_category", "other.uncategorized")
                ).category
            )
            loc_html = str(ev.get("location") or "")
            place = clean_text(loc_html, 200)
            room = clean_text(custom.get("Room Location") or custom.get("Campus room"), 120)
            lat = lon = None
            if m := _MAPS.search(loc_html):
                lat, lon = sane_coords(float(m.group(1)), float(m.group(2)), ctx)
            label = p.get("venue_label")
            venue = f"{label} – {place}" if label and place else place
            end = _when(ev.get("endDateTime"), ev.get("endTimeZoneOffset"), ctx.city.timezone)
            all_day = bool(ev.get("allDay"))
            if end is not None and all_day:
                end -= timedelta(seconds=1)  # all-day ends are exclusive midnights
            reg_note = (clean_text(custom.get("Registration Required")) or "").lower()
            required = bool(ev.get("openSignUp")) or (
                "required" in reg_note and "not required" not in reg_note and "no se requiere" not in reg_note
            )
            if ev.get("canceled"):
                availability = "cancelled"
            elif required and ev.get("reservationFull"):
                availability = "waitlist" if ev.get("waitingListAvailable") else "registration_closed"
            elif required:
                availability = "registration_open"
            else:
                availability = "unknown"
            offers = []
            action = ev.get("eventActionUrl")
            if ev.get("openSignUp") and isinstance(action, str) and action.startswith("http"):
                offers.append(
                    {
                        "seller": ctx.source.name,
                        "kind": "registration",
                        "url": action,
                        "availability": availability if availability != "unknown" else "registration_open",
                        "source_id": ctx.source.id,
                        "fetched_at": ctx.fetched_at,
                    }
                )
            web = _HREF.search(str(ev.get("webLink") or ""))
            url = ev.get("permaLinkUrl") or (web.group(1) if web else None)
            free = not ev.get("requiresPayment") and says_free(title, desc)
            yield ctx.base(
                str(ev["eventID"]),
                title=title,
                description=desc,
                url=url if isinstance(url, str) and url.startswith("http") else None,
                kind="recurring" if ev.get("repeats") else "one_off",
                recurrence=clean_text(ev.get("repeats"), 120),
                category=category,
                source_categories=cats,
                tags=[*p.get("tags", []), *(["registration_required"] if required else [])],
                start=start,
                end=end if end and end >= start else None,
                all_day=all_day,
                location={
                    "venue_name": f"{venue} ({room})" if venue and room else venue,
                    "lat": lat,
                    "lon": lon,
                    "geocode_method": "reported" if lat is not None else None,
                },
                organizer=clean_text(custom.get("Event sponsors")) or p.get("organizer"),
                price={"is_free": True} if free else {},
                availability=availability,
                offers=offers,
                extras={"series_id": str(ev["seriesID"])} if ev.get("seriesID") else {},
                _html=" ".join([desc_html, *custom.values(), str(ev.get("webLink") or "")]),
            )


def _when(value: Any, offset: Any, tz: str) -> Any:
    """Wall-clock ``2026-10-17T10:00:00`` + ``-0700`` → aware datetime (falls back to the city zone)."""
    if not value:
        return None
    if isinstance(offset, str) and _OFFSET.match(offset) and not re.search(r"(Z|[+-]\d\d:?\d\d)$", str(value)):
        return parse_dt(f"{value}{offset}", tz)
    return parse_dt(value, tz)
