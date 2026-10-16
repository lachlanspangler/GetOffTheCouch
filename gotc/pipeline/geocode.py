"""Geocoding with a permanent cache. US Census Geocoder first (keyless, US-only, public domain; batch file
first, then single-line), then OpenStreetMap Nominatim only as an **opt-in** fallback for place names.

Nominatim compliance (OSMF usage policy, https://operations.osmfoundation.org/policies/nominatim/, re-read
2026-10-16): "an absolute maximum of 1 request per second"; "Scripts running longer than a day and scripts
that are run at regular intervals are restricted to 4 requests per minute"; single thread, one machine, no
distributed scripts; "Results must be cached on your side"; "Clients sending repeatedly the same query may be
classified as faulty and blocked"; "periodic requests from apps are considered bulk geocoding and as such are
strongly discouraged". On top of that, nominatim.openstreetmap.org/robots.txt has ``Disallow: /search`` for
every user agent. So (docs/SOURCES.md, "Robots exceptions"):

  * Nominatim is OFF unless ``GOTC_NOMINATIM=1`` (an operator decision, never the default, never in CI shards)
  * when on: ≥ 15 s between requests (= 4/min), a hard per-run budget shared by all cities
    (``GOTC_NOMINATIM_BUDGET``, default 20), one lane (this process only)
  * every Nominatim answer, hit or miss, is cached forever and the same query is never sent twice

Every result carries a provider and a confidence; anything outside the city's radius is discarded rather
than plotted in the wrong state.
"""

from __future__ import annotations

import csv
import io
import logging
import os
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
NOMINATIM_HOST = "nominatim.openstreetmap.org"
NOMINATIM_INTERVAL_S = 15.0  # OSMF policy: recurring scripts ≤ 4 requests/minute


@dataclass(frozen=True)
class GeoResult:
    lat: float
    lon: float
    matched: str
    provider: str
    confidence: float


def nominatim_enabled() -> bool:
    return os.environ.get("GOTC_NOMINATIM", "").strip() == "1"


class Geocoder:
    def __init__(
        self,
        db: Database,
        http: PoliteClient | None,
        offline: bool = False,
        budget: int | None = None,
        nominatim: bool | None = None,
        nominatim_budget: int | None = None,
    ) -> None:
        self.db = db
        self.http = http
        self.offline = offline or http is None
        # max live Census lookups per city per run — politeness + bounded run time (CI sets GOTC_GEOCODE_BUDGET)
        self.budget = budget if budget is not None else int(os.environ.get("GOTC_GEOCODE_BUDGET", "150"))
        self.lookups = 0
        self.nominatim = nominatim_enabled() if nominatim is None else nominatim
        # hard per-RUN budget (not per city): at 15 s each, 20 lookups = 5 minutes of one lane
        self.nominatim_budget = (
            nominatim_budget if nominatim_budget is not None else int(os.environ.get("GOTC_NOMINATIM_BUDGET", "20"))
        )
        self.nominatim_lookups = 0
        if http is not None:
            # force, don't setdefault: a looser interval set elsewhere must never win
            http.host_intervals[NOMINATIM_HOST] = max(NOMINATIM_INTERVAL_S, http.host_intervals.get(NOMINATIM_HOST, 0))

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
        nominatim_tried = False
        if row is not None:
            if row["lat"] is not None:
                return GeoResult(row["lat"], row["lon"], row["matched"] or "", row["provider"], row["confidence"] or 0)
            nominatim_tried = "nominatim" in (row["provider"] or "")
            looked = datetime.fromisoformat(row["looked_up_at"])
            census_retry = utcnow() - looked >= MISS_TTL
            nominatim_open = self.nominatim and not nominatim_tried
            if self.offline or not (census_retry or nominatim_open):
                return None  # a recent miss: don't hammer the geocoder
            census_ok = census_retry
        else:
            census_ok = True
        if self.offline:
            return None
        cands = variants(query, city)
        res: GeoResult | None = None
        if census_ok and self.lookups < self.budget and any(re.search(r"\d", v) for v in cands):
            self.lookups += 1
            for variant in cands:
                res = self._census(variant, city)
                if res:
                    break
        if res is None and self.nominatim and not nominatim_tried:
            for variant in cands:
                if self.nominatim_lookups >= self.nominatim_budget:
                    break
                nominatim_tried = True
                res = self._nominatim(variant, city)
                if res:
                    break
        if res and haversine_m(res.lat, res.lon, *city.center) > city.radius_km * 1000 * 2.5:
            log.info("geocode %r landed outside %s; discarded", q, city.slug)
            res = None
        provider = res.provider if res else ("none:nominatim" if nominatim_tried else "none")
        self.db.execute(
            "INSERT OR REPLACE INTO geocode_cache (query, lat, lon, matched, provider, confidence, looked_up_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (
                key,
                res.lat if res else None,
                res.lon if res else None,
                res.matched if res else None,
                provider,
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
        self.nominatim_lookups += 1  # counted before the request: failures spend budget too
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
    no_room = re.sub(r"\s*\([^)]*\)", "", query).strip()  # "Northgate Branch (Meeting Room)" → "Northgate Branch"
    if no_room != query:
        out.append(_clean(no_room, city))
    query = no_room
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
