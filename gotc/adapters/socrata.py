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

The row → SourceEvent mapping (and every other mapping option: openings, privacy scrubbing, data-quality
guards, ``{today_date}``/``{asof_date}``/``{today_compact}`` placeholders) lives in ``gotc/adapters/mapped.py``.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.mapped import map_rows, window_fmt


@register
class SocrataAdapter(Adapter):
    name = "socrata"
    respect_robots = False  # documented public API

    def required_params(self) -> tuple[str, ...]:
        return ("domain", "dataset", "fields")

    def fetch(self, ctx: FetchContext) -> FetchResult:
        p = ctx.params
        self.check_config(ctx.source)
        fmt = window_fmt(ctx.now, ctx.city.timezone, p)
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
        rows = json.loads(payload.content)
        if not isinstance(rows, list):
            yield {"_reject": "payload is not a JSON array", "_hint": payload.text[:200]}
            return
        yield from map_rows(rows, ctx)
