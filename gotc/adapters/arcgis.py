"""ArcGIS REST FeatureServer / MapServer layers — config-driven, like Socrata. Powers many city GIS hubs.

Docs: https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/ .
Keyless. Query pattern::

    {service_url}/query?where=...&outFields=*&orderByFields=...&resultOffset=N&resultRecordCount=M&outSR=4326&f=geojson

Servers cap a page at their ``maxRecordCount`` and signal "there is more" with ``exceededTransferLimit``
(top level for ``f=json``, under ``properties`` for ``f=geojson``); we keep paging with ``resultOffset``
until it's gone. Dates are epoch milliseconds (``common.parse_dt`` and ``mapped.local_date`` handle them).
ArcGIS also returns errors as HTTP 200 with an ``{"error": {...}}`` body — treated as a fetch failure.

    params:
      service_url: https://services2.arcgis.com/<org>/arcgis/rest/services/<name>/FeatureServer/0
      where: "Date_Entered >= DATE '{today_date}'"      # placeholders: see mapped.window_fmt
      order_by: "Date_Entered DESC"
      format: geojson                                  # or json (attributes + geometry x/y)
      page_size: 1000
      fields: {record_id: Permit__, title: Business_Name, start: Date_Entered, address: [Address, City]}
      ...every other mapping option from gotc/adapters/mapped.py

Point geometry is exposed to the mapping as ``_lat``/``_lon`` (used when ``fields.lat``/``lon`` are absent).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.mapped import map_rows, window_fmt


@register
class ArcGISAdapter(Adapter):
    name = "arcgis"
    #: Documented public REST API (like Socrata). Esri-hosted ``services*.arcgis.com`` publish no robots policy:
    #: ``/robots.txt`` answers HTTP 403 "Invalid URL", which PoliteClient reads as "disallow everything".
    #: A self-hosted ArcGIS Server can opt back in per source with ``params.respect_robots: true``.
    respect_robots = False

    def required_params(self) -> tuple[str, ...]:
        return ("service_url", "fields")

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        fmt = window_fmt(ctx.now, ctx.city.timezone, p)
        url = p["service_url"].rstrip("/") + "/query"
        page_size = int(p.get("page_size", 1000))
        max_pages = int(p.get("max_pages", 10))
        out_format = p.get("format", "geojson")
        payloads: list[Payload] = []
        complete = True
        for page in range(max_pages):
            q: dict[str, str | int] = {
                "where": str(p.get("where", "1=1")).format(**fmt),
                "outFields": p.get("out_fields", "*"),
                "outSR": 4326,
                "resultOffset": page * page_size,
                "resultRecordCount": page_size,
                "f": out_format,
            }
            if order := p.get("order_by"):
                q["orderByFields"] = order
            r = ctx.http.get(url, params=q, respect_robots=bool(p.get("respect_robots", self.respect_robots)))
            data = r.json()
            if not isinstance(data, dict):
                raise ValueError(f"ArcGIS returned {type(data).__name__}, expected an object")
            if "error" in data:
                err = data["error"] if isinstance(data["error"], dict) else {"message": data["error"]}
                raise ValueError(f"ArcGIS error {err.get('code')}: {err.get('message')} {err.get('details') or ''}")
            if "features" not in data:
                raise ValueError("ArcGIS response has no 'features' — wrong layer id or service moved?")
            payloads.append(Payload.from_response(r, ctx.now, "json", page=page))
            if not _exceeded(data) or not data["features"]:
                break
        else:
            complete = False  # hit max_pages with more to come
        return FetchResult(payloads, complete=complete)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        data = json.loads(payload.content)
        if not isinstance(data, dict) or not isinstance(data.get("features"), list):
            yield {"_reject": "payload has no features list", "_hint": payload.text[:200]}
            return
        yield from map_rows((_row(ft) for ft in data["features"]), ctx)


def _exceeded(data: dict[str, Any]) -> bool:
    props = data.get("properties")
    if not isinstance(props, dict):
        props = {}
    return bool(data.get("exceededTransferLimit") or props.get("exceededTransferLimit"))


def _row(feature: Any) -> dict[str, Any]:
    """Flatten one feature (GeoJSON or Esri JSON) into a mapping row with ``_lat``/``_lon``."""
    if not isinstance(feature, dict):
        return {}
    row = dict(feature.get("properties") or feature.get("attributes") or {})
    geom = feature.get("geometry")
    if isinstance(geom, dict):
        coords = geom.get("coordinates")
        if geom.get("type") == "Point" and isinstance(coords, list) and len(coords) >= 2:
            row["_lon"], row["_lat"] = coords[0], coords[1]
        elif "x" in geom and "y" in geom:
            row["_lon"], row["_lat"] = geom["x"], geom["y"]
    return row
