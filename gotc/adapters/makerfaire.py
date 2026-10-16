"""Maker Faire global map feed — one JSON document listing every faire worldwide (~2,500 rows, ~1.9 MB).

    GET https://makerfaire.com/query/?type=map        (the JSON behind makerfaire.com/globalmap/)

Keyless; robots.txt allows everything except /wp-admin/ and /invoice/; make.co terms have no scraping clause
(research 2026-10-15). **Status 2026-10-16: Cloudflare answers our client with a 403 "Just a moment…" challenge**
(robots.txt itself is reachable). We don't get around challenges, so the source ships ``enabled: false`` until
Make: confirms access; the parser is tested against the research sample.

Global source (scope all_cities): each city keeps faires within ``max_km`` (default: the city's ``radius_km``) of
its center that haven't ended yet, and only the ``categories`` that are public faires (default Featured, Flagship,
Mini — "School" faires are closed events). Faraway / past faires are filtered, not rejected.

Dates arrive as "10/17/2026 12:00:00 am" with no time of day → all-day events in the city's timezone.
Coordinates are sometimes malformed ("-53.71733,17z"): we read the leading number and validate the range.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text, join_address
from gotc.pipeline.textnorm import haversine_m

URL = "https://makerfaire.com/query/?type=map"
DEFAULT_CATEGORIES = ("Featured", "Flagship", "Mini")


@register
class MakerFaireAdapter(Adapter):
    name = "makerfaire"

    def fetch(self, ctx: FetchContext) -> FetchResult:
        r = ctx.http.get(str(ctx.params.get("url", URL)))
        data = r.json()
        if not isinstance(data, dict) or not isinstance(data.get("Locations"), list):
            raise ValueError("Maker Faire map feed did not return {Locations: [...]} — endpoint changed?")
        return FetchResult([Payload.from_response(r, ctx.now, "json")], complete=True)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        data = json.loads(payload.content)
        tz = ZoneInfo(ctx.city.timezone)
        cats = {c.lower() for c in ctx.params.get("categories", DEFAULT_CATEGORIES)}
        max_km = float(ctx.params.get("max_km") or ctx.city.radius_km)
        today = ctx.fetched_at.astimezone(tz).date()
        for f in data.get("Locations") or []:
            lat, lon = _coord(f.get("lat"), 90), _coord(f.get("lng"), 180)
            if lat is None or lon is None:
                continue  # can't place it near any city (most are past/overseas); not a record for us
            km = haversine_m(ctx.city.center[0], ctx.city.center[1], lat, lon) / 1000
            if km > max_km or str(f.get("category") or "").lower() not in cats:
                continue
            start_d = _day(f.get("event_start_dt"))
            end_d = _day(f.get("event_end_dt")) or start_d
            if start_d is None:
                yield {"_reject": "faire without a parseable start date", "_hint": str(f.get("ID"))}
                continue
            if end_d is None or end_d < start_d:
                end_d = start_d
            if end_d < today - timedelta(days=1):
                continue  # already over
            title = clean_text(f.get("faire_name") or f.get("name"), 300)
            if not title:
                yield {"_reject": "faire without a name", "_hint": str(f.get("ID"))}
                continue
            site = _http(f.get("faire_url"))
            tickets = _http(f.get("ticket_site_url"))
            free = str(f.get("free_event") or "").strip().lower() in ("yes", "true", "1", "free")
            yield ctx.base(
                str(f.get("ID")),
                title=title,
                description=clean_text(f.get("description"), 2000) if f.get("description") != f.get("name") else None,
                url=site,
                kind="one_off",
                category="niche.maker_faire",
                source_categories=[c for c in (f.get("category"), f.get("event_type")) if c],
                start=datetime.combine(start_d, time(0, 0), tz),
                end=datetime.combine(end_d, time(23, 59), tz),
                all_day=True,
                location={
                    "address": join_address(
                        f.get("venue_address_street"),
                        f.get("venue_address_city"),
                        f.get("venue_address_state"),
                        f.get("venue_address_postal_code"),
                    ),
                    "lat": lat,
                    "lon": lon,
                    "geocode_method": "reported",
                },
                organizer="Maker Faire",
                price={"is_free": True} if free else {},
                availability="free_no_ticket" if free else "unknown",
                offers=[
                    {
                        "seller": "Maker Faire",
                        "kind": "primary",
                        "url": tickets,
                        "source_id": ctx.source.id,
                        "fetched_at": ctx.fetched_at,
                    }
                ]
                if tickets
                else [],
                extras={
                    "distance_km": round(km, 1),
                    "faire_year": str(f.get("faire_year") or "") or None,
                    "event_dt_text": clean_text(f.get("event_dt")),
                    "country": f.get("venue_address_country") or None,
                },
            )


def _coord(v: Any, bound: float) -> float | None:
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)", str(v or ""))
    if not m:
        return None
    f = float(m.group(1))
    return f if -bound <= f <= bound and f != 0.0 else None


def _day(v: Any) -> Any:
    try:
        return datetime.strptime(str(v).strip(), "%m/%d/%Y %I:%M:%S %p").date()  # noqa: DTZ007 — date only
    except ValueError:
        return None


def _http(v: Any) -> str | None:
    s = str(v or "").strip()
    return s if s.startswith(("http://", "https://")) else None
