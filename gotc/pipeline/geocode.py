"""Geocoding with a permanent cache. US Census Geocoder first (keyless, US-only, free, public domain),
then OpenStreetMap Nominatim as a fallback for place names (1 req/s, identified UA, results cached — per
https://operations.osmfoundation.org/policies/nominatim/).

Every result carries a provider and a confidence; anything outside the city's radius is discarded rather
than plotted in the wrong state.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

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
    def __init__(self, db: Database, http: PoliteClient | None, offline: bool = False, budget: int = 150) -> None:
        self.db = db
        self.http = http
        self.offline = offline or http is None
        self.budget = budget  # max live lookups per run — politeness + bounded run time
        self.lookups = 0
        if http is not None:
            http.host_intervals.setdefault("nominatim.openstreetmap.org", 1.1)

    def batch(self, queries: list[str], city: CityConfig) -> int:
        """Census batch geocoder (≤10,000 street addresses per POST, keyless). Fills the cache; returns hits.

        Only street addresses (with a house number) are sent; place names still go through ``geocode``.
        """
        if self.offline or self.http is None:
            return 0
        todo: dict[str, str] = {}
        for q in queries:
            c = _clean(q, city)
            if not c or not re.match(r"^\s*\d+[a-zA-Z]?\s", c):
                continue
            key = f"{city.slug}|{c.lower()}"
            if self.db.one("SELECT 1 FROM geocode_cache WHERE query = ?", (key,)) is None:
                todo[key] = c
        if not todo:
            return 0
        rows = []
        ids = list(todo)[:9000]
        for i, key in enumerate(ids):
            street = todo[key].split(",")[0].replace('"', "")
            zip_m = re.search(r"\b(\d{5})(?:-\d{4})?\b", todo[key])
            rows.append(f'{i},"{street}","{city.name}",{city.state},{zip_m.group(1) if zip_m else ""}')
        try:
            r = self.http.post(
                "https://geocoding.geo.census.gov/geocoder/locations/addressbatch",
                data={"benchmark": "Public_AR_Current"},
                files={"addressFile": ("addresses.csv", "\n".join(rows).encode(), "text/csv")},
                respect_robots=False,
            )
        except FetchError as e:
            log.warning("census batch geocode failed for %s: %s", city.slug, e)
            return 0
        hits = 0
        for line in csv.reader(io.StringIO(r.text)):
            if len(line) < 6 or not line[0].isdigit():
                continue
            key = ids[int(line[0])]
            res = None
            if line[2] == "Match" and "," in line[5]:
                lon_s, lat_s = line[5].split(",")[:2]
                res = GeoResult(
                    float(lat_s), float(lon_s), line[4], "census_batch", 0.9 if line[3] == "Exact" else 0.75
                )
                if haversine_m(res.lat, res.lon, *city.center) > city.radius_km * 1000 * 2.5:
                    res = None
            if res:
                hits += 1
            self.db.execute(
                "INSERT OR REPLACE INTO geocode_cache (query, lat, lon, matched, provider, confidence, looked_up_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    key,
                    res.lat if res else None,
                    res.lon if res else None,
                    res.matched if res else None,
                    res.provider if res else "census_batch:none",
                    res.confidence if res else None,
                    iso(utcnow()),
                ),
            )
        return hits

    def geocode(self, query: str, city: CityConfig) -> GeoResult | None:
        q = _clean(query, city)
        if not q:
            return None
        key = f"{city.slug}|{q.lower()}"
        row = self.db.one("SELECT * FROM geocode_cache WHERE query = ?", (key,))
        if row is not None:
            if row["lat"] is not None:
                return GeoResult(row["lat"], row["lon"], row["matched"] or "", row["provider"], row["confidence"] or 0)
            looked = datetime.fromisoformat(row["looked_up_at"])
            if utcnow() - looked < MISS_TTL or self.offline:
                return None  # a recent miss: don't hammer the geocoder
        if self.offline or self.lookups >= self.budget:
            return None
        self.lookups += 1
        res = None
        for variant in variants(query, city):
            res = self._census(variant, city) or self._nominatim(variant, city)
            if res:
                break
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


MISS_TTL = timedelta(days=30)


def variants(query: str, city: CityConfig) -> list[str]:
    """The raw place text first, then friendlier forms: "Miami-Dade Public Library – West Kendall Regional"
    → "West Kendall Regional Library"."""
    out = [_clean(query, city)]
    parts = re.split(r"\s+[–—-]\s+", query, maxsplit=1)
    if len(parts) == 2:
        left, right = parts
        if "library" in left.lower() and "library" not in right.lower():
            out.append(_clean(f"{right} Library", city))
        out.append(_clean(right, city))
    return list(dict.fromkeys(v for v in out if v))


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
