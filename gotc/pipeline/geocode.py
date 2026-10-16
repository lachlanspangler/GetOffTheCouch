"""Geocoding with a permanent cache. US Census Geocoder first (keyless, US-only, free, public domain),
then OpenStreetMap Nominatim as a fallback for place names (1 req/s, identified UA, results cached — per
https://operations.osmfoundation.org/policies/nominatim/).

Every result carries a provider and a confidence; anything outside the city's radius is discarded rather
than plotted in the wrong state.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from gotc.config import CityConfig
from gotc.http.client import FetchError, PoliteClient
from gotc.pipeline.textnorm import haversine_m
from gotc.storage.db import Database, iso, utcnow

log = logging.getLogger(__name__)

CENSUS = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
NOMINATIM = "https://nominatim.openstreetmap.org/search"


@dataclass(frozen=True)
class GeoResult:
    lat: float
    lon: float
    matched: str
    provider: str
    confidence: float


class Geocoder:
    def __init__(self, db: Database, http: PoliteClient | None, offline: bool = False, budget: int = 200) -> None:
        self.db = db
        self.http = http
        self.offline = offline or http is None
        self.budget = budget  # max live lookups per run — politeness + bounded run time
        self.lookups = 0
        if http is not None:
            http.host_intervals.setdefault("nominatim.openstreetmap.org", 1.1)

    def geocode(self, query: str, city: CityConfig) -> GeoResult | None:
        q = _clean(query, city)
        if not q:
            return None
        key = f"{city.slug}|{q.lower()}"
        row = self.db.one("SELECT * FROM geocode_cache WHERE query = ?", (key,))
        if row is not None:
            if row["lat"] is None:
                return None
            return GeoResult(row["lat"], row["lon"], row["matched"] or "", row["provider"], row["confidence"] or 0)
        if self.offline or self.lookups >= self.budget:
            return None
        self.lookups += 1
        res = self._census(q, city) or self._nominatim(q, city)
        if res and haversine_m(res.lat, res.lon, *city.center) > city.radius_km * 1000 * 2.5:
            log.info("geocode %r landed outside %s; discarded", q, city.slug)
            res = None
        self.db.execute(
            "INSERT OR REPLACE INTO geocode_cache (query, lat, lon, matched, provider, confidence, looked_up_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (
                key,
                res.lat if res else None,
                res.lon if res else None,
                res.matched if res else None,
                res.provider if res else "none",
                res.confidence if res else None,
                iso(utcnow()),
            ),
        )
        return res

    def _census(self, q: str, city: CityConfig) -> GeoResult | None:
        if not re.search(r"\d", q):  # Census needs a street address; place names go to Nominatim
            return None
        assert self.http is not None
        try:
            data = self.http.get_json(
                CENSUS,
                params={"address": q, "benchmark": "Public_AR_Current", "format": "json"},
                respect_robots=False,
            )
        except (FetchError, ValueError):
            return None
        matches = (data.get("result") or {}).get("addressMatches") or []
        if not matches:
            return None
        m = matches[0]
        c = m.get("coordinates") or {}
        return GeoResult(float(c["y"]), float(c["x"]), m.get("matchedAddress", ""), "census", 0.95)

    def _nominatim(self, q: str, city: CityConfig) -> GeoResult | None:
        assert self.http is not None
        lat, lon = city.center
        d = city.radius_km / 111.0
        try:
            data = self.http.get_json(
                NOMINATIM,
                params={
                    "q": q,
                    "format": "jsonv2",
                    "limit": 1,
                    "countrycodes": "us",
                    "viewbox": f"{lon - d * 1.4},{lat + d},{lon + d * 1.4},{lat - d}",
                    "bounded": 1,
                },
                respect_robots=False,
            )
        except (FetchError, ValueError):
            return None
        if not data:
            return None
        top = data[0]
        conf = 0.8 if top.get("addresstype") in ("building", "amenity", "leisure", "shop", "tourism") else 0.6
        return GeoResult(float(top["lat"]), float(top["lon"]), top.get("display_name", ""), "nominatim", conf)


def _clean(query: str, city: CityConfig) -> str:
    q = re.sub(r"\s+", " ", query).strip(" ,")
    if not q or len(q) < 4:
        return ""
    q = re.sub(r"(?i)\b(between|btwn\.?)\b.*?(,|$)", r"\2", q)  # NYC permits: "X between A and B"
    low = q.lower()
    if city.name.lower() not in low and not any(a.lower() in low for a in city.aliases):
        q = f"{q}, {city.name}, {city.state}"
    elif f", {city.state.lower()}" not in low:
        q = f"{q}, {city.state}"
    return q
