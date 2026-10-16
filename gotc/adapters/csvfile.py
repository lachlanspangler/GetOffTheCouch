"""Plain CSV file downloads (state license extracts, open-data "download CSV" links) — config-driven, like Socrata.

Some agencies publish only a nightly CSV file, no query API (Florida DBPR's alcoholic-beverage license extracts).
This adapter downloads the file (conditional GET: ``Last-Modified``/``ETag`` make unchanged days cheap), decodes
it, turns each line into a row dict and hands the rows to ``gotc.adapters.mapped.map_rows`` — so every mapping
option, the privacy scrubbing (``PII_KEY``) and ``entity_only_fields`` work exactly as for Socrata/ArcGIS/CKAN.

    params:
      url: https://www2.myfloridalicense.com/sto/file_download/extracts/bd4006lic.csv
      encoding: [utf-8, cp1252]        # tried in order (strict); the last one always decodes (with replacement)
      columns: [profession, county, …]  # for headerless files: positional column names (else the header row is used)
      delimiter: ","
      window: {field: original_licensure_date, lookback_days: 60}   # keep rows dated in [today - N, today + ahead_days]
      legal_name_copies: {dba: owner_name}   # see below
      fields: {record_id: license_number, title: [dba, dba_legal], start: original_licensure_date, …}
      ...every other mapping option from gotc/adapters/mapped.py (include / exclude / exclude_regex / templates …)

**Header names are normalized to snake_case** ("Owner Name" → ``owner_name``, "Mail Address 1" →
``mail_address_1``) before anything else. That keeps config keys simple and — more importantly — lets
``mapped.PII_KEY`` recognise personal-data columns (``owner…``, ``mail_…``) that a header with spaces would hide.

**Window.** Files are whole-table snapshots with no server-side filter, so rows outside the ``window`` (or with
no date in that column) are *filtered*, not rejected: they're valid, just not news.

**legal_name_copies** ``{a: b}``: when column *a* (a trade name / DBA) merely repeats column *b* (the licensee's
legal name, which may be a person), the value moves to ``a_legal``. List ``a_legal`` in ``entity_only_fields``
and as the title fallback, and a DBA that is really a person's name is withheld unless it looks like an
organisation ("… LLC", "… Restaurant"). Column *b* itself is dropped by the privacy scrub when its name matches
``PII_KEY`` (``owner_name`` does).
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterator
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.mapped import local_date, map_rows

_NON_WORD = re.compile(r"[^0-9a-z]+")


def snake(name: str) -> str:
    """'Location Address 1' → 'location_address_1'; '﻿Board' → 'board'."""
    return _NON_WORD.sub("_", name.replace("﻿", "").strip().lower()).strip("_")


def decode(content: bytes, encodings: list[str]) -> tuple[str, str]:
    """Decode with the first encoding that works strictly; the last one is forced (errors replaced)."""
    for enc in encodings[:-1]:
        try:
            return content.decode(enc), enc
        except UnicodeDecodeError:
            continue
    last = encodings[-1]
    return content.decode(last, errors="replace"), last


@register
class CSVFileAdapter(Adapter):
    name = "csvfile"

    def required_params(self) -> tuple[str, ...]:
        return ("url", "fields")

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        r = ctx.http.get(str(ctx.params["url"]))
        if not r.content.strip():
            raise ValueError(f"{ctx.params['url']}: empty file")
        if r.content.lstrip()[:1] == b"<":
            raise ValueError(f"{ctx.params['url']}: got HTML, not CSV — moved or blocked?")
        return FetchResult([Payload.from_response(r, ctx.now, "csv")], complete=True)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        yield from map_rows(self.rows(payload, ctx), ctx)

    def rows(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        p = ctx.params
        enc = p.get("encoding") or ["utf-8-sig", "cp1252"]
        text, _used = decode(payload.content, [enc] if isinstance(enc, str) else list(enc))
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=str(p.get("delimiter", ",")))
        columns = [snake(c) for c in p["columns"]] if p.get("columns") else None
        if columns is None:
            header = next(reader, None)
            if header is None:
                return
            columns = [snake(c) for c in header]
        window = p.get("window") or {}
        tz = ctx.city.timezone
        today = ctx.fetched_at.astimezone(ZoneInfo(tz)).date()
        lo = today - timedelta(days=int(window.get("lookback_days", p.get("lookback_days", 60))))
        hi = today + timedelta(days=int(window.get("ahead_days", 0)))
        copies: dict[str, str] = {snake(k): snake(v) for k, v in (p.get("legal_name_copies") or {}).items()}
        for values in reader:
            if not any(v.strip() for v in values):
                continue
            if len(values) != len(columns):
                yield {"_reject": f"row has {len(values)} columns, expected {len(columns)}", "_hint": "<row>"}
                continue
            row = {c: v.strip() for c, v in zip(columns, values, strict=True)}
            if window.get("field"):
                d = local_date(row.get(snake(window["field"])), tz)
                if d is None or not (lo <= d <= hi):
                    continue  # outside the window / undated: not news (filtered, not rejected)
            for a, b in copies.items():
                if row.get(a) and _norm(row.get(a)) == _norm(row.get(b)):
                    row[f"{a}_legal"], row[a] = row[a], ""
            yield row


def _norm(v: Any) -> str:
    return re.sub(r"[\s.,]+", " ", str(v or "")).strip().lower()
