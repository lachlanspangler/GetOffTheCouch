"""Generic calendar-platform adapters. Each covers *thousands* of sites, so a new city is usually just config.

  tribe      — The Events Calendar (WordPress) REST API: /wp-json/tribe/events/v1/events
               (parks boards, breweries, venues, clubs, chambers of commerce)
  localist   — Localist /api/2/events (universities, cities, tourism boards)
  livewhale  — LiveWhale /live/json/events (universities)

All keyless, documented, public JSON. robots.txt is still honored (they're site endpoints, not API hosts).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import timedelta
from typing import Any
from urllib.parse import urljoin

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text, join_address, money, parse_dt, prices_in_text, says_free


def _classify(ctx: ParseContext, title: str, cats: list[str], desc: str | None) -> str:
    cmap: dict[str, str] = ctx.params.get("category_map", {})
    for c in cats:
        if c in cmap:
            return cmap[c]
    if not ctx.params.get("classify_description", True):
        desc = None  # venue blurbs ("the band will play…") mislead the keyword classifier; title + labels only
    return ctx.tax.classify(
        title, " ".join(cats), desc, default=ctx.params.get("default_category", "other.uncategorized")
    ).category


def _price(cost_text: Any, values: list[Any], desc: str | None, title: str) -> tuple[dict[str, Any], str]:
    if isinstance(cost_text, int | float):  # some LiveWhale installs send cost as a bare number
        values, cost_text = [*values, cost_text], None
    elif cost_text is not None:
        cost_text = str(cost_text)
    nums = [v for v in (money(x) for x in values) if v is not None] or prices_in_text(cost_text)
    nums = nums or prices_in_text(title)  # "Route 3 $25": some venues only put the cover in the title
    if nums and max(nums) > 0:
        return {"min": min(nums), "max": max(nums), "note": clean_text(cost_text, 80)}, "unknown"
    if (cost_text and "free" in cost_text.lower()) or (nums and max(nums) == 0) or says_free(title, desc):
        return {"is_free": True}, "free_no_ticket"
    return {}, "unknown"


@register
class TribeEventsAdapter(Adapter):
    name = "tribe"

    def required_params(self) -> tuple[str, ...]:
        return ("base_url",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        url = urljoin(p["base_url"].rstrip("/") + "/", "wp-json/tribe/events/v1/events")
        local = ctx.now.astimezone(_zone(ctx.city.timezone))
        q: dict[str, str | int] = {
            "start_date": local.strftime("%Y-%m-%d 00:00:00"),
            "end_date": (local + timedelta(days=int(p.get("horizon_days", 60)))).strftime("%Y-%m-%d 23:59:59"),
            "per_page": int(p.get("per_page", 50)),
            "status": "publish",
        }
        if cats := p.get("categories"):
            q["categories"] = ",".join(cats)
        payloads: list[Payload] = []
        complete = True
        for page in range(1, int(p.get("max_pages", 20)) + 1):
            q["page"] = page
            r = ctx.http.get(url, params=q)
            data = r.json()
            if not isinstance(data, dict) or "events" not in data:
                raise ValueError("tribe endpoint did not return {events: [...]} — plugin changed or removed?")
            payloads.append(Payload.from_response(r, ctx.now, "json", page=page))
            if page >= int(data.get("total_pages") or 1):
                break
        else:
            complete = False
        return FetchResult(payloads, complete=complete)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        data = json.loads(payload.content)
        for ev in data.get("events", []):
            title = clean_text(ev.get("title"), 300)
            tz = ev.get("timezone") or ctx.city.timezone
            if not str(tz).count("/"):
                tz = ctx.city.timezone  # "UTC-5" style offsets: fall back to the city's zone
            start = parse_dt(ev.get("start_date"), tz)
            if not title or start is None:
                yield {"_reject": "missing title/start", "_hint": str(ev.get("id"))}
                continue
            desc = clean_text(ev.get("description"), 4000)
            cats = [clean_text(c.get("name")) or "" for c in ev.get("categories") or []]
            tags = [clean_text(t.get("name")) or "" for t in ev.get("tags") or []]
            venue = ev.get("venue") if isinstance(ev.get("venue"), dict) else {}
            orgs = ev.get("organizer") if isinstance(ev.get("organizer"), list) else []
            price, avail = _price(ev.get("cost"), (ev.get("cost_details") or {}).get("values") or [], desc, title)
            lat, lon = _ll(venue.get("geo_lat")), _ll(venue.get("geo_lng"))
            if lat is None or lon is None:
                lat = lon = None
            venue_name = clean_text(venue.get("venue"))
            address = join_address(venue.get("address"), venue.get("city"), venue.get("state"), venue.get("zip"))
            if not venue_name and not address:  # single-venue calendars often leave the venue blank
                fallback = ctx.params.get("venue") or {}
                venue_name, address = fallback.get("name"), fallback.get("address")
            yield ctx.base(
                str(ev["id"]),
                title=title,
                description=desc,
                url=ev.get("url") or ev.get("website") or None,
                category=_classify(ctx, title, cats + tags, desc),
                source_categories=[c for c in cats + tags if c],
                tags=list(ctx.params.get("tags", [])),
                start=start,
                end=parse_dt(ev.get("end_date"), tz),
                all_day=bool(ev.get("all_day")),
                location={
                    "venue_name": venue_name,
                    "address": address,
                    "lat": lat,
                    "lon": lon,
                    "geocode_method": "reported" if lat is not None else None,
                },
                organizer=clean_text(orgs[0].get("organizer")) if orgs else ctx.params.get("organizer"),
                price=price,
                availability=avail,
                _html=ev.get("description"),
            )


@register
class LocalistAdapter(Adapter):
    """Localist: https://developer.localist.com/doc/api — GET /api/2/events?days=N&pp=100&page=P

    Filters: ``type: <id>`` (one filter ID) or ``types: [<id>, …]`` (any of several, sent as ``type[]=``); the IDs
    come from ``GET /api/2/events/filters`` (e.g. a "General Public" audience or public event types).
    """

    name = "localist"

    def required_params(self) -> tuple[str, ...]:
        return ("base_url",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        url = p["base_url"].rstrip("/") + "/api/2/events"
        if types := p.get("types"):
            # any-of filter IDs: Localist ORs repeated `type[]=` values (a repeated plain `type=` ANDs them)
            url += "?" + "&".join(f"type%5B%5D={int(t)}" for t in types)
        payloads: list[Payload] = []
        complete = True
        for page in range(1, int(p.get("max_pages", 10)) + 1):
            q: dict[str, str | int] = {
                "days": min(370, int(p.get("horizon_days", 60))),
                "pp": 100,
                "page": page,
            }
            for k in ("type", "keyword", "venue_id"):
                if k in p:
                    q[k] = p[k]
            r = ctx.http.get(url, params=q)
            data = r.json()
            payloads.append(Payload.from_response(r, ctx.now, "json", page=page))
            if page >= int((data.get("page") or {}).get("total") or 1):
                break
        else:
            complete = False
        return FetchResult(payloads, complete=complete)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        data = json.loads(payload.content)
        for wrap in data.get("events", []):
            ev = wrap.get("event", wrap)
            title = clean_text(ev.get("title"), 300)
            insts = [i.get("event_instance", i) for i in ev.get("event_instances") or []]
            if not title or not insts:
                yield {"_reject": "missing title/instances", "_hint": str(ev.get("id"))}
                continue
            desc = clean_text(ev.get("description_text") or ev.get("description"), 4000)
            filters = ev.get("filters") or {}
            cats = [f.get("name", "") for group in filters.values() if isinstance(group, list) for f in group]
            cats += [str(t) for t in ev.get("tags") or []]
            free = bool(ev.get("free"))
            price, avail = _price(ev.get("ticket_cost"), [], desc, title)
            if free and not price.get("min"):
                price, avail = {"is_free": True}, "free_no_ticket"
            geo = ev.get("geo") or {}
            lat, lon = _ll(geo.get("latitude")), _ll(geo.get("longitude"))
            if lat is None or lon is None:
                lat = lon = None
            for inst in insts[: int(ctx.params.get("max_occurrences", 4))]:
                start = parse_dt(inst.get("start"), ctx.city.timezone)
                if start is None:
                    continue
                yield ctx.base(
                    f"{ev['id']}:{inst.get('id', start.isoformat())}",
                    title=title,
                    description=desc,
                    url=ev.get("localist_url") or ev.get("url") or None,
                    kind="recurring" if len(insts) > 1 else "one_off",
                    category=_classify(ctx, title, cats, desc),
                    source_categories=cats,
                    tags=list(ctx.params.get("tags", [])),
                    start=start,
                    end=parse_dt(inst.get("end"), ctx.city.timezone),
                    all_day=bool(inst.get("all_day")),
                    location={
                        "venue_name": clean_text(ev.get("location_name") or ev.get("venue_name")),
                        "address": clean_text(ev.get("address")),
                        "lat": lat,
                        "lon": lon,
                        "geocode_method": "reported" if lat is not None else None,
                    },
                    organizer=clean_text((ev.get("departments") or [{}])[0].get("name"))
                    if ev.get("departments")
                    else ctx.params.get("organizer"),
                    price=price,
                    availability=avail,
                    offers=[
                        {
                            "seller": ctx.source.name,
                            "kind": "registration" if "regist" in (ev.get("ticket_url") or "") else "primary",
                            "url": ev["ticket_url"],
                            "source_id": ctx.source.id,
                            "fetched_at": ctx.fetched_at,
                        }
                    ]
                    if str(ev.get("ticket_url") or "").startswith("http")
                    else [],
                    _html=ev.get("description"),
                )


@register
class LiveWhaleAdapter(Adapter):
    """LiveWhale Calendar JSON: <base>/live/json/events/max/N (universities)."""

    name = "livewhale"

    def required_params(self) -> tuple[str, ...]:
        return ("base_url",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        path = p.get("path", "/live/json/events/max/{max}")
        url = p["base_url"].rstrip("/") + path.format(max=int(p.get("max", 200)))
        r = ctx.http.get(url)
        if not isinstance(r.json(), list | dict):
            raise ValueError("livewhale did not return JSON")
        return FetchResult([Payload.from_response(r, ctx.now, "json")], complete=False)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        data = json.loads(payload.content)
        items = data if isinstance(data, list) else data.get("data") or data.get("events") or []
        for ev in items:
            title = clean_text(ev.get("title"), 300)
            start = parse_dt(
                ev.get("date_iso") or ev.get("date_utc") or ev.get("date"),
                ev.get("timezone") or ctx.city.timezone,
            )
            if not title or start is None:
                yield {"_reject": "missing title/start", "_hint": str(ev.get("id"))}
                continue
            desc = clean_text(ev.get("summary") or ev.get("description"), 4000)
            cats = [str(c) for c in (ev.get("event_types") or [])] + [str(t) for t in (ev.get("tags") or [])]
            price, avail = _price(ev.get("cost"), [], desc, title)
            lat, lon = _ll(ev.get("location_latitude")), _ll(ev.get("location_longitude"))
            if lat is None or lon is None:
                lat = lon = None
            yield ctx.base(
                str(ev.get("id")),
                title=title,
                description=desc,
                url=ev.get("url") or None,
                category=_classify(ctx, title, cats, desc),
                source_categories=cats,
                tags=list(ctx.params.get("tags", [])),
                start=start,
                end=parse_dt(ev.get("date2_iso") or ev.get("date2_utc"), ctx.city.timezone),
                all_day=bool(ev.get("is_all_day")),
                location={
                    "venue_name": clean_text(ev.get("location")),
                    "address": clean_text(ev.get("location_address") or ev.get("location")),
                    "lat": lat,
                    "lon": lon,
                    "geocode_method": "reported" if lat is not None else None,
                },
                organizer=clean_text(ev.get("group_title")) or ctx.params.get("organizer"),
                price=price,
                availability=avail,
            )


def _ll(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f != 0.0 else None


def _zone(tz: str) -> Any:
    from zoneinfo import ZoneInfo

    return ZoneInfo(tz)
