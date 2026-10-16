"""Socrata Open Data (SODA 2.x) — config-driven. Powers most US city open-data portals.

Docs: https://dev.socrata.com/docs/queries/ . Keyless; an optional free app token
(``SOCRATA_APP_TOKEN``) raises rate limits. Field names differ per dataset, so the mapping lives in config:

    params:
      domain: data.cityofnewyork.us
      dataset: tvpp-9vvx
      where: "start_date_time >= '{today}' AND start_date_time < '{horizon}'"
      order: start_date_time
      fields: {record_id: event_id, title: event_name, start: start_date_time, end: end_date_time,
               address: event_location, area: event_borough, category: event_type}
      category_map: {"Block Party": community.block_party, "Street Event": community.block_party}
      default_category: community.festival
      exclude: {event_type: ["Production Event"]}
      title_template: "{event_name}"           # optional, python format over the raw row
      tags: [outdoor]                           # optional, applied to every record
      free: true                                # optional: source guarantees free admission
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register, stable_id
from gotc.adapters.common import clean_text, dig, join_address, parse_dt, title_case_if_shouty


class _SafeDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return ""


@register
class SocrataAdapter(Adapter):
    name = "socrata"
    respect_robots = False  # documented public API

    def required_params(self) -> tuple[str, ...]:
        return ("domain", "dataset", "fields")

    def fetch(self, ctx: FetchContext) -> FetchResult:
        p = ctx.params
        self.check_config(ctx.source)
        horizon_days = int(p.get("horizon_days", 120))
        lookback_days = int(p.get("lookback_days", 0))
        local_today = ctx.now.astimezone(_tz(ctx.city.timezone)).date()
        fmt = {
            "today": (local_today - timedelta(days=lookback_days)).isoformat() + "T00:00:00",
            "horizon": (local_today + timedelta(days=horizon_days)).isoformat() + "T00:00:00",
            "since": (local_today - timedelta(days=int(p.get("since_days", 45)))).isoformat() + "T00:00:00",
        }
        page_size = int(p.get("page_size", 1000))
        max_pages = int(p.get("max_pages", 10))
        headers = {}
        if token := ctx.settings.secret("SOCRATA_APP_TOKEN"):
            headers["X-App-Token"] = token
        url = f"https://{p['domain']}/resource/{p['dataset']}.json"
        payloads: list[Payload] = []
        complete = True
        for page in range(max_pages):
            q: dict[str, str | int] = {"$limit": page_size, "$offset": page * page_size}
            if where := p.get("where"):
                q["$where"] = where.format(**fmt)
            if order := p.get("order"):
                q["$order"] = order
            if select := p.get("select"):
                q["$select"] = select
            r = ctx.http.get(url, params=q, headers=headers, respect_robots=False)
            payloads.append(Payload.from_response(r, ctx.now, "json", page=page))
            rows = r.json()
            if not isinstance(rows, list):
                raise ValueError(f"expected a JSON array from {url}, got {type(rows).__name__}")
            if len(rows) < page_size:
                break
        else:
            complete = False  # hit max_pages: there may be more rows; don't mark absent records gone
        return FetchResult(payloads, complete=complete)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        p = ctx.params
        f: dict[str, str] = p["fields"]
        tz = ctx.city.timezone
        rows = json.loads(payload.content)
        cmap: dict[str, str] = p.get("category_map", {})
        exclude: dict[str, list[str]] = p.get("exclude", {})
        include: dict[str, list[str]] = p.get("include", {})
        for row in rows:
            if any(str(row.get(k, "")) in vals for k, vals in exclude.items()):
                continue
            if include and not all(str(row.get(k, "")) in vals for k, vals in include.items()):
                continue
            title = row.get(f["title"]) if "title" in f else None
            if tmpl := p.get("title_template"):
                title = tmpl.format_map(_SafeDict(row)).strip(" -–·")
            title = clean_text(title, 300)
            start = parse_dt(dig(row, f["start"]), tz)
            if not title or start is None:
                yield {"_reject": "missing title or start", "_hint": json.dumps(row)[:200]}
                continue
            rid_field = f.get("record_id")
            rid = str(row[rid_field]) if rid_field and row.get(rid_field) else None
            rid = rid or stable_id(title, start.isoformat(), dig(row, f.get("address", ""), ""))
            # one permit can cover many dates; make the id unique per occurrence
            if p.get("id_includes_start", True):
                rid = f"{rid}:{start.date().isoformat()}"
            raw_cat = str(dig(row, f["category"], "")) if "category" in f else ""
            desc = clean_text(dig(row, f["description"]) if "description" in f else None, 4000)
            category = cmap.get(raw_cat)
            if not category:
                cls = ctx.tax.classify(title, desc, raw_cat, default=p.get("default_category", "other.uncategorized"))
                category = cls.category
            lat = _num(dig(row, f["lat"])) if "lat" in f else None
            lon = _num(dig(row, f["lon"])) if "lon" in f else None
            if lat is None or lon is None:
                lat = lon = None
            address = join_address(
                *(dig(row, k) for k in _as_list(f.get("address"))),
                dig(row, f["area"]) if "area" in f else None,
            )
            url = dig(row, f["url"]) if "url" in f else None
            if isinstance(url, dict):
                url = url.get("url")
            yield ctx.base(
                rid,
                title=title_case_if_shouty(title),
                description=desc,
                url=url or p.get("default_url"),
                kind=p.get("kind", "one_off"),
                category=category,
                source_categories=[raw_cat] if raw_cat else [],
                tags=list(p.get("tags", [])),
                start=start,
                end=parse_dt(dig(row, f["end"]), tz) if "end" in f else None,
                location={
                    "venue_name": clean_text(dig(row, f["venue"])) if "venue" in f else None,
                    "address": address,
                    "neighborhood": clean_text(dig(row, f["neighborhood"])) if "neighborhood" in f else None,
                    "lat": lat,
                    "lon": lon,
                    "geocode_method": "reported" if lat is not None else None,
                },
                organizer=clean_text(dig(row, f["organizer"])) if "organizer" in f else None,
                price={"is_free": True} if p.get("free") else {},
                availability="free_no_ticket" if p.get("free") else "unknown",
            )


def _as_list(v: Any) -> list[str]:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _tz(name: str) -> Any:
    from zoneinfo import ZoneInfo

    return ZoneInfo(name)
