"""HandsOn Connect volunteer calendars (Boston Cares, Hands On Nashville, L.A. Works, NYC Service, UW Austin…).

    POST <base_url>/search/getOpportunitiesCalendar
         searchvo_startfrom=YYYY-MM-DD & searchvo_endfrom=YYYY-MM-DD & searchvo_searchresultblockid=<block_id>

This is the JSON endpoint the tenant's own /calendar page calls (request shape taken from the site's JS bundle;
research 2026-10-15). Keyless; every tenant's robots.txt is a 404 (no rules) — still checked on every run.
Responses are large (Boston ≈ 70 KB per day), so we query **small windows** (``window_days``, 1–3) up to
``horizon_days`` ahead, ≥3 s apart. The block id is the ``calendar-search-block-id`` hidden input on /calendar
(some tenants, e.g. L.A. Works, need none).

Availability comes from ``volunteersStillNeeded``: 0 means the shift is full — HOC tenants then offer
"Add to Waiting list … Currently full" on the opportunity page (verified on bostoncares.org 2026-10-16), so we
report ``waitlist``. Shifts have no separate sign-up deadline in the feed; we don't invent one.

    params:
      base_url: https://www.bostoncares.org
      block_id: 589
      horizon_days: 14
      window_days: 2
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register, stable_id
from gotc.adapters.common import clean_text, join_address, parse_dt
from gotc.pipeline.normalize import location_from_text

ENDPOINT = "/search/getOpportunitiesCalendar"


def _none(v: Any) -> Any:
    """HOC serializes nulls as the string 'None'."""
    return None if v is None or (isinstance(v, str) and v.strip() in ("", "None", "null")) else v


def _int(v: Any) -> int | None:
    v = _none(v)
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


@register
class HandsOnConnectAdapter(Adapter):
    name = "handsonconnect"

    def required_params(self) -> tuple[str, ...]:
        return ("base_url",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        url = str(p["base_url"]).rstrip("/") + ENDPOINT
        window = max(1, min(3, int(p.get("window_days", 2))))
        horizon = max(1, int(p.get("horizon_days", 14)))
        day = ctx.now.astimezone(ZoneInfo(ctx.city.timezone)).date()
        last = day + timedelta(days=horizon - 1)
        payloads: list[Payload] = []
        complete = True
        while day <= last:
            end = min(last, day + timedelta(days=window - 1))
            form: dict[str, str | int | float] = {
                "searchvo_startfrom": day.isoformat(),
                "searchvo_endfrom": end.isoformat(),
            }
            if p.get("block_id"):
                form["searchvo_searchresultblockid"] = str(p["block_id"])
            r = ctx.http.post(url, data=form)
            data = r.json()
            if not isinstance(data, dict) or str(data.get("code")) != "200" or not isinstance(data.get("items"), list):
                msg = data.get("message") if isinstance(data, dict) else type(data).__name__
                raise ValueError(f"HandsOn Connect calendar returned no items ({msg!r}) — endpoint changed?")
            if any(str(d.get("overMaxToReturn")).lower() == "true" for d in data["items"]):
                complete = False  # a day was truncated server-side: don't mark missing shifts gone
            payloads.append(Payload.from_response(r, ctx.now, "json", start=day.isoformat(), end=end.isoformat()))
            day = end + timedelta(days=1)
        return FetchResult(payloads, complete=complete)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        data = json.loads(payload.content)
        for day in data.get("items") or []:
            # day["events"] holds campaign banners ("Season of Sharing": name/description/eventLink, no date or
            # shift) — the campaign's shifts are already in "occurrences", so the banners aren't records.
            for occ in day.get("occurrences") or []:
                yield _occurrence(occ, ctx)


def _occurrence(o: dict[str, Any], ctx: ParseContext) -> dict[str, Any]:
    title = clean_text(_none(o.get("opportunityName")), 300)
    tz = _tz(_none(o.get("timezone")), ctx.city.timezone)
    start = parse_dt(_none(o.get("startDateTimeISO")), tz)
    link = _none(o.get("opportunityLink"))
    if not title or start is None:
        return {"_reject": "occurrence without name/start", "_hint": str(o.get("occurrenceId") or link)}
    end = parse_dt(_none(o.get("endDateTimeISO")), tz)
    desc_html = _none(o.get("description"))
    desc_text = clean_text(desc_html, 4000)
    sched = str(_none(o.get("scheduledType")) or "")
    ongoing = bool(sched) and "specific" not in sched.lower()
    default = "volunteer.recurring" if ongoing else "volunteer.one_off"
    cls = ctx.tax.classify(title, default=default)
    category = cls.category if cls.category == "volunteer.board" else default
    spots = _int(o.get("volunteersStillNeeded"))
    if spots is None:
        avail = "registration_open"
    elif spots == 0:
        avail = "waitlist"
    elif spots <= 2:
        avail = "few_left"
    else:
        avail = "registration_open"
    loc_type = str(_none(o.get("locationType")) or "")
    virtual = loc_type.lower() == "virtual"
    city_part = _none(o.get("locationCity"))
    state_zip = " ".join(x for x in (_none(o.get("locationState")), _none(o.get("locationZipCode"))) if x)
    managing = clean_text(_none(o.get("managingOrganization")))
    rid = str(_none(o.get("occurrenceId")) or stable_id(link, start.isoformat()))
    offers = (
        [
            {
                "seller": managing or ctx.source.name,
                "kind": "registration",
                "url": link,
                "listing_count": None,
                "availability": avail,
                "source_id": ctx.source.id,
                "fetched_at": ctx.fetched_at,
            }
        ]
        if str(link or "").startswith("http")
        else []
    )
    return ctx.base(
        rid,
        title=title,
        description=desc_text,
        url=link if str(link or "").startswith("http") else None,
        kind="recurring" if ongoing else "one_off",
        category=category,
        source_categories=[c for c in (_none(o.get("opportunityType")), sched or None, *_areas(o)) if c],
        start=start,
        end=end if end and end >= start else None,
        timezone=tz,
        location=_location(desc_text, virtual, join_address(city_part, state_zip)),
        organizer=clean_text(_none(o.get("organizationServedName"))) or managing,
        offers=offers,
        registration={"url": link, "method": "reported"} if offers else None,
        availability=avail,
        extras={
            "spots_left": spots,
            "max_attendance": _int(o.get("maximumAttendance")),
            "location_type": loc_type or None,
            "location_city": city_part,
            "virtual": virtual,
            "opportunity_type": _none(o.get("opportunityType")),
            "scheduled_type": sched or None,
            "managed_by": _none(o.get("managedBy")),
            "managing_org": managing,
            "organization_served_id": _none(o.get("organizationServedId")),
        },
        _html=desc_html,
    )


def _location(desc: str | None, virtual: bool, area: str | None) -> dict[str, Any]:
    """The feed only has city/neighborhood + ZIP; many descriptions carry a 'Location: Venue (street, city)' line."""
    if virtual:
        return {}
    found = location_from_text(desc)
    if found:
        m = re.match(r"^(.*?)\s*\((.+)\)\s*$", found)
        venue, addr = (m.group(1), m.group(2)) if m else (found.split(",")[0], found)
        return {"venue_name": venue.strip()[:120] or None, "address": addr.strip(), "neighborhood": None}
    return {"address": area}


def _areas(o: dict[str, Any]) -> list[str]:
    """issueAreas arrives as a list or as a stringified Python list ("['Arts & Culture']")."""
    raw = o.get("issueAreas")
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    return [a or b for a, b in re.findall(r"'([^']+)'|\"([^\"]+)\"", str(raw or ""))]


def _tz(value: Any, fallback: str) -> str:
    if not value or "/" not in str(value):
        return fallback
    try:
        ZoneInfo(str(value))
    except (ZoneInfoNotFoundError, ValueError):
        return fallback
    return str(value)
