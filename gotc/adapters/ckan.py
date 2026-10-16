"""CKAN DataStore (data.boston.gov and many state/city portals) — config-driven, like Socrata.

Docs: https://docs.ckan.org/en/latest/maintaining/datastore.html#ckanext.datastore.logic.action.datastore_search_sql
Keyless. We use ``datastore_search_sql`` so filtering/sorting happens server-side::

    {base_url}/api/3/action/datastore_search_sql?sql=SELECT * FROM "<resource>" WHERE ... ORDER BY ... LIMIT n OFFSET m

Resource ids can change when a city re-publishes a dataset, so prefer ``package`` (the dataset slug): the
current DataStore resource is resolved with ``package_show`` on every fetch (``resource_name`` picks one
when a package has several). Boston stores every column as ``text``; ISO date strings compare correctly.

    params:
      base_url: https://data.boston.gov
      package: food-establishment-inspections      # or resource_id: f1e13724-...
      resource_name: Active Food Establishment Licenses   # optional, when the package has several tables
      where: "descript = 'Eating & Drinking' AND license_add_dt_tm >= '{today_date}'"
      order: "license_add_dt_tm DESC"
      page_size: 500
      fields: {record_id: property_id, title: [dbaname, businessname], start: license_add_dt_tm, ...}
      ...every other mapping option from gotc/adapters/mapped.py

Column names with spaces must be double-quoted in ``where``/``order`` (``"Start Date and Time"``).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from gotc.adapters.base import Adapter, AdapterConfigError, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.mapped import map_rows, window_fmt


@register
class CKANAdapter(Adapter):
    name = "ckan"

    def required_params(self) -> tuple[str, ...]:
        return ("base_url", "fields")

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        api = p["base_url"].rstrip("/") + "/api/3/action/"
        resource = p.get("resource_id") or self._resolve(ctx, api)
        fmt = window_fmt(ctx.now, ctx.city.timezone, p)
        page_size = int(p.get("page_size", 500))
        max_pages = int(p.get("max_pages", 10))
        payloads: list[Payload] = []
        complete = True
        for page in range(max_pages):
            sql = f'SELECT * FROM "{resource}"'
            if where := p.get("where"):
                sql += f" WHERE {where.format(**fmt)}"
            if order := p.get("order"):
                sql += f" ORDER BY {order}"
            sql += f" LIMIT {page_size} OFFSET {page * page_size}"
            r = ctx.http.get(api + "datastore_search_sql", params={"sql": sql})
            data = r.json()
            if not isinstance(data, dict) or not data.get("success"):
                err = data.get("error") if isinstance(data, dict) else data
                raise ValueError(f"CKAN datastore_search_sql failed: {str(err)[:300]}")
            payloads.append(Payload.from_response(r, ctx.now, "json", page=page, resource=resource))
            if len((data.get("result") or {}).get("records") or []) < page_size:
                break
        else:
            complete = False
        return FetchResult(payloads, complete=complete)

    def _resolve(self, ctx: FetchContext, api: str) -> str:
        p = ctx.params
        if "package" not in p:
            raise AdapterConfigError(f"{ctx.source.id}: set params.package or params.resource_id")
        data = ctx.http.get(api + "package_show", params={"id": p["package"]}).json()
        if not isinstance(data, dict) or not data.get("success"):
            raise ValueError(f"CKAN package_show {p['package']!r} failed")
        resources = [r for r in data["result"].get("resources", []) if r.get("datastore_active")]
        if name := p.get("resource_name"):
            resources = [r for r in resources if str(r.get("name", "")).strip().lower() == name.strip().lower()]
        if not resources:
            raise ValueError(
                f"CKAN package {p['package']!r} has no DataStore resource named {p.get('resource_name')!r}"
            )
        return str(resources[0]["id"])

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        data = json.loads(payload.content)
        records = (data.get("result") or {}).get("records") if isinstance(data, dict) else None
        if not isinstance(records, list):
            yield {"_reject": "payload has no result.records list", "_hint": payload.text[:200]}
            return
        # ``_full_text`` is CKAN's search index of the whole row (it tokenizes phone numbers too): never map it
        rows = ({k: v for k, v in r.items() if k != "_full_text"} if isinstance(r, dict) else r for r in records)
        yield from map_rows(rows, ctx)
