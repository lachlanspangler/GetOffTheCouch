"""Config-driven row → SourceEvent mapping, shared by the tabular open-data adapters (Socrata, ArcGIS, CKAN).

Open-data portals hand us flat rows whose column names differ per dataset, so the mapping lives in config
and a new dataset needs no code. Every key below is optional except ``fields.title`` and ``fields.start``::

    params:
      fields:                       # column names in the raw row (dotted paths allowed: "georeference.coordinates.1")
        record_id: license_id
        title: [dba, legalname]     # a list = first non-empty value wins
        start: originalissuedate
        end: expirationdate
        address: [street, city]     # a list = joined with ", "
        area: borough               # appended to the address
        lat: latitude
        lon: longitude
        latlon: coordinates         # alternative: one "lat, lon" string column
        category: description       # raw label, looked up in category_map
        description: comments
        url: link
        venue: location_name
        neighborhood: neighborhood
        organizer: agency
        attendance: expected_attendance   # a count the source reports → reported_attendance
      title_template: "{title} — new liquor license"   # python format over the row; {title} = resolved title
      description_template: "..."                      # same, plus {date} (human start date)
      category_map: {"Club": nightlife.opening}         # raw category label → taxonomy id
      category_rules: [{match: "(?i)\\bbar\\b", category: nightlife.opening}]   # regex on title + raw category
      default_category: food_drink.restaurant_opening
      include: {field: [values]} / exclude: {field: [values]}           # exact-match row filters
      include_regex: {field: regex} / exclude_regex: {field: regex}     # regex row filters
      exclude_title: ["(?i)\\bwedding\\b"]                              # regex denylist on the title
      entity_only_fields: [legalname]  # only use these as a title if they look like a business, never a person
      validate: {license_number: "^\\d{2}-\\d+$"}  # reject rows whose field doesn't match (data-quality guard)
      reject_future_start: true        # reject rows dated after today (e.g. swapped date/number columns)
      max_future_days: 400             # reject rows dated absurdly far ahead (e.g. year 2109 typos)
      kind: opening                    # SourceEvent.kind
      all_day: true                    # start is a date; emitted as local midnight with all_day=True
      id_includes_start: true          # default: one permit covering many dates → one record per date
      tags: [outdoor]  free: true  default_url: https://...  extras: {signal: license}

Privacy: columns that hold personal data (owner, applicant, manager, contact, phone, e-mail, mailing address)
are dropped from every row *before* mapping, so no config — and no template — can ever emit them.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable, Iterator
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from gotc.adapters.base import ParseContext, stable_id
from gotc.adapters.common import clean_text, dig, join_address, parse_dt, title_case_if_shouty

#: column names that carry personal data. Matched case-insensitively against every row key.
PII_KEY = re.compile(
    r"(?i)(phone|phn|(^|_)(cell|mobile|fax|tel)($|_)|owner|manager|applicant|contact|e_?mail|^mail_|mailing|"
    r"requestor|(^|_)ssn($|_)|birth|first_?name|last_?name|^agent)"
)
_PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
#: a legal name that is clearly an organisation, not a person
_ENTITY = re.compile(
    r"(?i)\b(llc|l\.l\.c|inc|incorporated|corp|corporation|co|company|ltd|limited|lp|llp|pllc|pc|plc|"
    r"group|holdings?|partners(hip)?|enterprises?|ventures?|associates|association|assn|foundation|"
    r"society|conservancy|club|church|council|trust|fund|university|college|school|alliance|coalition|"
    r"institute|center|centre|museum|league|chamber|hospitality|restaurants?|bar|tavern|pub|grill|"
    r"cafe|kitchen|brewing|brewery|distillery|winery|hotel|inn|lounge|market|foods?|catering)\b\.?"
)
#: default bar-vs-restaurant split for kind=opening when config gives no category
OPENING_NIGHTLIFE = re.compile(
    r"(?i)\b(bar|bars|tavern|pub|saloon|lounge|cocktails?|night ?club|club|cabaret|brew(ery|ing|pub)|"
    r"taproom|tap room|tap house|taphouse|beer (hall|garden)|biergarten|wine bar|speakeasy|distillery|"
    r"cantina|karaoke|jazz|dive|ale ?house|drinking places)\b"
)


class _SafeDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return ""


def window_fmt(now: datetime, tz: str, params: dict[str, Any]) -> dict[str, str]:
    """Date placeholders for ``where`` templates, computed in the city's timezone.

    ``{today}``/``{today_date}``/``{today_compact}`` honor ``lookback_days`` (start of the window);
    ``{asof_date}`` is always the real local date; ``{horizon*}`` = today + ``horizon_days``.
    """
    local_today = now.astimezone(ZoneInfo(tz)).date()
    start = local_today - timedelta(days=int(params.get("lookback_days", 0)))
    horizon = local_today + timedelta(days=int(params.get("horizon_days", 120)))
    since = local_today - timedelta(days=int(params.get("since_days", 45)))
    out: dict[str, str] = {}
    for name, d in (("today", start), ("horizon", horizon), ("since", since), ("asof", local_today)):
        out[name] = d.isoformat() + "T00:00:00"
        out[f"{name}_date"] = d.isoformat()
        out[f"{name}_compact"] = d.strftime("%Y%m%d")
    return out


def scrub_row(row: dict[str, Any], extra: Iterable[str] = ()) -> dict[str, Any]:
    """Drop personal-data columns (see ``PII_KEY``) plus any configured ``drop_fields``."""
    drop = set(extra)
    return {k: v for k, v in row.items() if k not in drop and not PII_KEY.search(k)}


def looks_like_entity(name: str | None) -> bool:
    return bool(name and _ENTITY.search(name))


def scrub_phones(text: str | None) -> str | None:
    return _PHONE.sub("[phone removed]", text) if text else text


def local_date(value: Any, tz: str) -> date | None:
    """The calendar date a date-ish value means, in the city's zone.

    Date-only columns are often stored as UTC midnight (ArcGIS epoch ms, ``...T00:00:00Z``); converting
    those to a US zone would shift them to the previous evening, so UTC-midnight values keep their UTC date.
    """
    if value is None or value == "":
        return None
    if isinstance(value, int | float) or (isinstance(value, str) and re.fullmatch(r"-?\d{11,13}", value)):
        ms = float(value)
        dt = datetime.fromtimestamp(ms / (1000 if abs(ms) > 1e11 else 1), tz=ZoneInfo("UTC"))
    else:
        parsed = parse_dt(value, tz)
        if parsed is None:
            return None
        dt = parsed
    if dt.utcoffset() == timedelta(0) and dt.time() == time(0, 0):
        return dt.date()
    return dt.astimezone(ZoneInfo(tz)).date()


def _first(row: dict[str, Any], spec: Any, entity_only: set[str]) -> str | None:
    for key in spec if isinstance(spec, list) else [spec]:
        val = clean_text(dig(row, key))
        if not val:
            continue
        if key in entity_only and not looks_like_entity(val):
            continue  # a legal name that may be a person: never use it as a title
        return val
    return None


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def sane_coords(lat: float | None, lon: float | None, ctx: ParseContext) -> tuple[float | None, float | None]:
    """Drop coordinates that are missing, (0,0), or far outside the city (placeholder geometry)."""
    if lat is None or lon is None or (abs(lat) < 1 and abs(lon) < 1):
        return None, None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, None
    limit = max(ctx.city.radius_km * 4, 80.0)
    if _km((lat, lon), ctx.city.center) > limit:
        return None, None
    return lat, lon


def map_rows(rows: Iterable[dict[str, Any]], ctx: ParseContext) -> Iterator[dict[str, Any]]:
    p = ctx.params
    f: dict[str, Any] = p["fields"]
    tz = ctx.city.timezone
    cmap: dict[str, str] = p.get("category_map", {})
    rules = [(re.compile(r["match"]), r["category"]) for r in p.get("category_rules", [])]
    exclude: dict[str, list[str]] = p.get("exclude", {})
    include: dict[str, list[str]] = p.get("include", {})
    deny_title = [re.compile(x) for x in p.get("exclude_title", [])]
    include_rx = {k: re.compile(v) for k, v in p.get("include_regex", {}).items()}
    exclude_rx = {k: re.compile(v) for k, v in p.get("exclude_regex", {}).items()}
    validate = {k: re.compile(v) for k, v in p.get("validate", {}).items()}
    entity_only = set(p.get("entity_only_fields", []))
    kind = p.get("kind", "one_off")
    all_day = bool(p.get("all_day", kind == "opening"))
    today = ctx.fetched_at.astimezone(ZoneInfo(tz)).date()
    max_future = p.get("max_future_days")
    drop = p.get("drop_fields", [])

    for raw in rows:
        if not isinstance(raw, dict):
            yield {"_reject": "row is not an object", "_hint": str(raw)[:200]}
            continue
        if any(str(raw.get(k, "")) in vals for k, vals in exclude.items()):
            continue
        if include and not all(str(raw.get(k, "")) in vals for k, vals in include.items()):
            continue
        if any(not rx.search(str(dig(raw, k, ""))) for k, rx in include_rx.items()):
            continue
        if any(rx.search(str(dig(raw, k, ""))) for k, rx in exclude_rx.items()):
            continue
        row = scrub_row(raw, drop)
        hint = json.dumps({k: v for k, v in row.items() if k not in entity_only}, default=str)[:200]
        bad = [k for k, rx in validate.items() if not rx.search(str(row.get(k) or ""))]
        if bad:
            yield {"_reject": f"failed data-quality check on {', '.join(bad)}", "_hint": hint}
            continue

        name = _first(row, f.get("title"), entity_only) if "title" in f else None
        name = title_case_if_shouty(name) if name else None
        if tmpl := p.get("title_template"):
            title = clean_text(tmpl.format_map(_SafeDict(row, title=name or "")).strip(" -–—·"), 300)
            if not name and "{title}" in tmpl:
                title = None
        else:
            title = clean_text(name, 300)
        if all_day:
            d = local_date(dig(row, f["start"]), tz)
            start = datetime.combine(d, time(0, 0), ZoneInfo(tz)) if d else None
        else:
            start = parse_dt(dig(row, f["start"]), tz)
        if not title or start is None:
            withheld = not name and any(clean_text(dig(row, k)) for k in entity_only)
            reason = (
                "no business name (legal name may be a person's; withheld)" if withheld else "missing title or start"
            )
            yield {"_reject": reason, "_hint": hint}
            continue
        title = title_case_if_shouty(title)
        if any(rx.search(title) for rx in deny_title):
            continue
        if p.get("reject_future_start") and start.date() > today:
            yield {"_reject": f"start {start.date()} is in the future (swapped columns?)", "_hint": hint}
            continue
        if max_future is not None and start.date() > today + timedelta(days=int(max_future)):
            yield {"_reject": f"start {start.date()} is implausibly far ahead", "_hint": hint}
            continue

        rid_field = f.get("record_id")
        rid = str(dig(row, rid_field)) if rid_field and dig(row, rid_field) not in (None, "") else None
        rid = rid or stable_id(title, start.isoformat(), dig(row, _first_key(f.get("address")), ""))
        if p.get("id_includes_start", kind != "opening"):  # one permit can cover many dates
            rid = f"{rid}:{start.date().isoformat()}"

        raw_cat = (clean_text(dig(row, f["category"])) or "") if "category" in f else ""
        desc_field = clean_text(dig(row, f["description"]), 4000) if "description" in f else None
        category = cmap.get(raw_cat)
        if not category:
            category = next((c for rx, c in rules if rx.search(f"{name or title} {raw_cat}")), None)
        if not category and kind == "opening":
            hay = " ".join(x for x in (name or title, raw_cat) if x)
            nightlife = OPENING_NIGHTLIFE.search(hay)
            category = "nightlife.opening" if nightlife else p.get("default_category", "food_drink.restaurant_opening")
        if not category:
            default = p.get("default_category", "other.uncategorized")
            category = ctx.tax.classify(title, desc_field, raw_cat, default=default).category

        if dtmpl := p.get("description_template"):
            human = start.strftime("%b %-d, %Y")
            desc = clean_text(dtmpl.format_map(_SafeDict(row, title=name or title, date=human)), 4000)
            if desc_field:
                desc = f"{desc}\n\n{desc_field}" if desc else desc_field
        else:
            desc = desc_field
        if kind == "opening":
            desc = scrub_phones(desc)

        lat = _num(dig(row, f["lat"])) if "lat" in f else _num(row.get("_lat"))
        lon = _num(dig(row, f["lon"])) if "lon" in f else _num(row.get("_lon"))
        if "latlon" in f:  # a single "40.71, -73.99" string column
            parts = str(dig(row, f["latlon"], "")).replace(";", ",").split(",")
            lat, lon = (_num(parts[0]), _num(parts[1])) if len(parts) == 2 else (None, None)
        lat, lon = sane_coords(lat, lon, ctx)
        address = join_address(
            *(clean_text(dig(row, k)) for k in _as_list(f.get("address"))),
            clean_text(dig(row, f["area"])) if "area" in f else None,
        )
        url = dig(row, f["url"]) if "url" in f else None
        if isinstance(url, dict):
            url = url.get("url")
        if not (isinstance(url, str) and url.startswith(("http://", "https://"))):
            url = None
        end = None
        if "end" in f and all_day:
            end_day = local_date(dig(row, f["end"]), tz)
            if end_day and end_day > start.date():  # multi-day permit: through the end of its last day
                end = datetime.combine(end_day, time(23, 59), ZoneInfo(tz))
        elif "end" in f:
            end = parse_dt(dig(row, f["end"]), tz)
            if end is not None and end < start:
                end = None
        extras: dict[str, Any] = dict(p.get("extras", {}))
        if raw_cat:
            extras.setdefault("source_label", raw_cat[:120])
        yield ctx.base(
            rid,
            title=title,
            description=desc,
            url=url or p.get("default_url"),
            kind=kind,
            category=category,
            source_categories=[raw_cat] if raw_cat else [],
            tags=list(p.get("tags", [])),
            start=start,
            end=end,
            all_day=all_day,
            location={
                "venue_name": clean_text(dig(row, f["venue"])) if "venue" in f else None,
                "address": address,
                "neighborhood": clean_text(dig(row, f["neighborhood"])) if "neighborhood" in f else None,
                "lat": lat,
                "lon": lon,
                "geocode_method": "reported" if lat is not None else None,
            },
            organizer=clean_text(dig(row, f["organizer"])) if "organizer" in f else p.get("organizer"),
            reported_attendance=_attendance(dig(row, f["attendance"])) if "attendance" in f else None,
            price={"is_free": True} if p.get("free") else {},
            availability="free_no_ticket" if p.get("free") else "unknown",
            extras=extras,
            # raw description HTML lets normalize.py lift sign-up/ticket links (never for license rows)
            _html=str(dig(row, f["description"], "")) or None if "description" in f and kind != "opening" else None,
        )


def _attendance(v: Any) -> int | None:
    n = _num(str(v).replace(",", "")) if v not in (None, "") else None
    return int(n) if n and n >= 1 else None


def _as_list(v: Any) -> list[str]:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _first_key(v: Any) -> str:
    keys = _as_list(v)
    return keys[0] if keys else ""
