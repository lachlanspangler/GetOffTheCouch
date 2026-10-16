"""Simpleview CVB event calendars (tourism boards: Visit Denver, Visit Austin, Meet Boston, …).

This is the JSON API the boards' own event-calendar pages call. It is **undocumented** (no public ToS for
it), so we treat it as medium-risk: the sites' robots.txt allow it (they disallow only ``/plugins/crm/count/``
and ask for ``Crawl-delay: 2``, which PoliteClient honors), we make at most a handful of requests a day,
cache, attribute "via <board>", and drop the source if a board objects or blocks it.

Two steps:
  1. ``GET {base}/plugins/core/get_simple_token/`` → a short-lived 32-hex token (text/plain)
  2. ``GET {base}/includes/rest_v2/plugins_events_events_by_date/find/?json=<query>&token=<token>``
     where ``<query>`` is a Mongo-style filter: ``{"filter": {"active": true, "date_range": {...}},
     "options": {"limit", "skip", "count": true, "fields": {...}, "sort": {...}}}``

``events_by_date`` returns each event **once** with ``date`` = its next occurrence inside the window, stored
as the *local end of day* in UTC (``2026-10-17T03:59:59Z`` = Oct 16 in Boston). ``startTime``/``endTime`` are
local wall-clock; ``startDate``/``endDate`` are the whole run. ``recurType`` 0 = one-off; 1/2/3/99 = repeating.

    params:
      base_url: https://visitdenver.com
      horizon_days: 7
      skip_daily_ongoing_days: 60    # daily "events" running longer than this are attractions, not events
      category_map: {Free Events: ..., Beer: food_drink.tasting}    # checked in config order
      default_category: community.festival
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text, combine_date_time, money, parse_dt, prices_in_text, says_free
from gotc.adapters.mapped import sane_coords

FIELDS = [
    "recid", "title", "date", "startDate", "endDate", "recurType", "recurrence", "startTime", "endTime",
    "location", "address1", "city", "state", "zip", "latitude", "longitude", "url", "linkUrl", "admission",
    "categories", "listing.title", "description",
]  # fmt: skip
_TOKEN = re.compile(r"^[0-9a-f]{16,64}$")


@register
class SimpleviewAdapter(Adapter):
    name = "simpleview"

    def required_params(self) -> tuple[str, ...]:
        return ("base_url",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        base = p["base_url"].rstrip("/")
        token = ctx.http.get(f"{base}/plugins/core/get_simple_token/", conditional=False).text.strip()
        if not _TOKEN.match(token):
            raise ValueError("Simpleview token endpoint did not return a token — site changed?")
        zone = ZoneInfo(ctx.city.timezone)
        local = ctx.now.astimezone(zone).date()
        start = datetime.combine(local, time(0, 0), zone).astimezone(ZoneInfo("UTC"))
        end = start + timedelta(days=int(p.get("horizon_days", 7)))
        page_size = int(p.get("page_size", 200))
        payloads: list[Payload] = []
        complete = True
        for page in range(int(p.get("max_pages", 10))):
            query = {
                "filter": {
                    "active": True,
                    "$and": [{"categories.catId": {"$exists": True}}],
                    "date_range": {"start": {"$date": _z(start)}, "end": {"$date": _z(end)}},
                },
                "options": {
                    "limit": page_size,
                    "skip": page * page_size,
                    "count": True,
                    "castDocs": False,
                    "fields": dict.fromkeys(FIELDS, 1),
                    "sort": {"date": 1, "rank": 1, "title_sort": 1},
                },
            }
            r = ctx.http.get(
                f"{base}/includes/rest_v2/plugins_events_events_by_date/find/",
                params={"json": json.dumps(query, separators=(",", ":")), "token": token},
                conditional=False,
            )
            docs = (r.json() or {}).get("docs")
            if not isinstance(docs, dict) or not isinstance(docs.get("docs"), list):
                raise ValueError("Simpleview find did not return {docs: {count, docs}} — API changed?")
            payloads.append(Payload.from_response(r, ctx.now, "json", page=page))
            if (page + 1) * page_size >= int(docs.get("count") or 0) or not docs["docs"]:
                break
        else:
            complete = False
        return FetchResult(payloads, complete=complete)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        p = ctx.params
        tz = ctx.city.timezone
        zone = ZoneInfo(tz)
        base = p.get("base_url", "").rstrip("/")
        board = p.get("board", ctx.source.name)
        cmap: dict[str, str] = p.get("category_map", {})
        ongoing_limit = int(p.get("skip_daily_ongoing_days", 60))
        data = json.loads(payload.content)
        docs = ((data or {}).get("docs") or {}).get("docs") if isinstance(data, dict) else None
        if not isinstance(docs, list):
            yield {"_reject": "payload has no docs.docs list", "_hint": payload.text[:200]}
            return
        for ev in docs:
            if not isinstance(ev, dict):
                yield {"_reject": "doc is not an object", "_hint": str(ev)[:200]}
                continue
            title = clean_text(ev.get("title"), 300)
            occurrence = parse_dt(ev.get("date"), tz)
            if not ev.get("recid") or not title or occurrence is None:
                yield {"_reject": "missing recid/title/date", "_hint": json.dumps(ev)[:200]}
                continue
            day = occurrence.astimezone(zone).date()
            run_start = parse_dt(ev.get("startDate"), tz)
            recur = int(ev.get("recurType") or 0)
            if recur == 1 and run_start and (day - run_start.astimezone(zone).date()).days > ongoing_limit:
                continue  # a daily "event" running for months is an attraction (museum, cruise), not an event
            start = combine_date_time(day.isoformat(), ev.get("startTime"), tz)
            if start is None:
                yield {"_reject": "unparseable occurrence date", "_hint": json.dumps(ev)[:200]}
                continue
            all_day = not ev.get("startTime")
            end = combine_date_time(day.isoformat(), ev.get("endTime"), tz) if ev.get("endTime") else None
            if end is not None and end < start:
                end += timedelta(days=1)  # "22:00 – 02:00"
            html = ev.get("description")
            desc = clean_text(html, 4000)
            cats = [clean_text(c.get("catName")) or "" for c in ev.get("categories") or [] if isinstance(c, dict)]
            cats = [c for c in cats if c]
            category = (
                next((cmap[k] for k in cmap if k in cats), None)
                or ctx.tax.classify(
                    title, " ".join(cats), desc, default=p.get("default_category", "other.uncategorized")
                ).category
            )
            admission = clean_text(ev.get("admission"), 120)
            nums = prices_in_text(admission) or ([m] if (m := money(admission)) and "$" in (admission or "") else [])
            if nums and max(nums) > 0:
                price: dict[str, Any] = {"min": min(nums), "max": max(nums), "note": admission}
                availability = "unknown"
            elif (admission and says_free(admission)) or {"Free", "Free Events"} & set(cats):
                price, availability = {"is_free": True}, "free_no_ticket"
            else:
                price, availability = ({"note": admission} if admission else {}), "unknown"
            lat, lon = sane_coords(_f(ev.get("latitude")), _f(ev.get("longitude")), ctx)
            rel = ev.get("url")
            url = f"{base}{rel}" if isinstance(rel, str) and rel.startswith("/") and base else ev.get("linkUrl")
            link = ev.get("linkUrl")
            run_end = parse_dt(ev.get("endDate"), tz)
            recurrence = clean_text(ev.get("recurrence"), 80) if recur else None
            if recur and run_end:
                until = run_end.astimezone(zone).strftime("%b %-d")
                recurrence = f"{recurrence}, through {until}" if recurrence else f"Through {until}"
            yield ctx.base(
                str(ev["recid"]),
                title=title,
                description=desc,
                url=url if isinstance(url, str) and url.startswith("http") else None,
                kind="recurring" if recur else "one_off",
                recurrence=recurrence,
                category=category,
                source_categories=cats,
                tags=list(p.get("tags", [])),
                start=start,
                end=end,
                all_day=all_day,
                location={
                    "venue_name": clean_text(ev.get("location"), 200)
                    or clean_text((ev.get("listing") or {}).get("title"), 200),
                    "address": clean_text(
                        ", ".join(
                            str(x) for x in (ev.get("address1"), ev.get("city"), ev.get("state"), ev.get("zip")) if x
                        )
                    ),
                    "lat": lat,
                    "lon": lon,
                    "geocode_method": "reported" if lat is not None else None,
                },
                organizer=clean_text((ev.get("listing") or {}).get("title")) or board,
                price=price,
                availability=availability,
                offers=[
                    {
                        "seller": board,
                        "kind": "info",
                        "url": link,
                        "source_id": ctx.source.id,
                        "fetched_at": ctx.fetched_at,
                    }
                ]
                if isinstance(link, str) and link.startswith("http")
                else [],
                extras={"via": board},
                _html=html,
            )


def _z(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _f(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
