"""Weather for outdoor events from the US National Weather Service (api.weather.gov): keyless, public domain,
US-only — a perfect fit. Two calls per city (points → hourly forecast), cached 3h in SQLite.

NWS asks for an identifying User-Agent (we send one) and caching (we do). If NWS is down, events simply
carry no forecast and the failure is logged; the build never fails because of weather.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta

from gotc.config import CityConfig
from gotc.http.client import FetchError, PoliteClient
from gotc.schema import Event, Weather
from gotc.storage.db import Database, iso, parse_iso
from gotc.taxonomy import Taxonomy

log = logging.getLogger(__name__)
TTL = timedelta(hours=3)
OUTDOOR_FAMILIES = {"outdoors", "fitness", "sports_league", "community"}


_OUTDOOR_HINT = re.compile(
    r"\b(park|garden|trail|lake|river|creek|beach|patio|rooftop|outdoor|field|cleanup|buckthorn)\b", re.I
)


def is_outdoor(ev: Event, tax: Taxonomy) -> bool:
    """Weather is shown when it plausibly matters. Used only for the forecast, never for the 'Outdoors' tag."""
    if "indoor" in ev.tags:
        return False
    if "outdoor" in ev.tags or tax.top(ev.category) in OUTDOOR_FAMILIES:
        return True
    return bool(_OUTDOOR_HINT.search(f"{ev.title} {ev.location.venue_name or ''}"))


def hourly(
    db: Database, http: PoliteClient | None, city: CityConfig, now: datetime
) -> tuple[list[dict[str, object]], datetime | None]:
    row = db.one("SELECT fetched_at, data FROM weather_cache WHERE city = ?", (city.slug,))
    if row and (http is None or now - (parse_iso(row["fetched_at"]) or now) < TTL):
        return json.loads(row["data"]), parse_iso(row["fetched_at"])
    if http is None:
        return [], None
    lat, lon = city.center
    try:
        pts = http.get_json(
            f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}",
            respect_robots=False,
            headers={"Accept": "application/geo+json"},
        )
        url = pts["properties"]["forecastHourly"]
        fc = http.get_json(url, respect_robots=False, headers={"Accept": "application/geo+json"})
    except (FetchError, KeyError, ValueError) as e:
        log.warning("NWS forecast unavailable for %s: %s", city.slug, e)
        return (json.loads(row["data"]), parse_iso(row["fetched_at"])) if row else ([], None)
    periods = [
        {
            "start": p["startTime"],
            "end": p["endTime"],
            "temp_f": p.get("temperature"),
            "precip_pct": (p.get("probabilityOfPrecipitation") or {}).get("value"),
            "short": p.get("shortForecast"),
        }
        for p in fc["properties"]["periods"]
    ]
    db.execute(
        "INSERT OR REPLACE INTO weather_cache (city, fetched_at, data) VALUES (?, ?, ?)",
        (city.slug, iso(now), json.dumps(periods)),
    )
    return periods, now


def attach(events: list[Event], periods: list[dict[str, object]], fetched_at: datetime | None, tax: Taxonomy) -> int:
    if not periods or fetched_at is None:
        return 0
    parsed = [(datetime.fromisoformat(str(p["start"])), datetime.fromisoformat(str(p["end"])), p) for p in periods]
    n = 0
    for ev in events:
        if ev.all_day or not is_outdoor(ev, tax):
            continue
        hit = next((p for s, e, p in parsed if s <= ev.start < e), None)
        if hit is None:
            continue
        ev.weather = Weather(
            short=str(hit["short"] or ""),
            temp_f=float(hit["temp_f"]) if hit["temp_f"] is not None else None,  # type: ignore[arg-type]
            precip_pct=float(hit["precip_pct"]) if hit["precip_pct"] is not None else None,  # type: ignore[arg-type]
            fetched_at=fetched_at,
        )
        n += 1
    return n
