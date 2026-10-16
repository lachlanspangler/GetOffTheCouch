"""Venue capacities from Wikidata (P1083 "maximum capacity"), keyless SPARQL, cached a week per city.

Demolished/closed venues (P576 dissolved, P3999 closure date) are excluded. Multiple capacity statements →
the largest (configurations vary; the fill-rate band absorbs the difference). Each venue keeps its QID so the
UI can link the source of the number.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from gotc.config import CityConfig
from gotc.http.client import FetchError, PoliteClient
from gotc.storage.db import Database, iso, parse_iso

log = logging.getLogger(__name__)
TTL = timedelta(days=7)
ENDPOINT = "https://query.wikidata.org/sparql"
QUERY = """
SELECT ?v ?vLabel (MAX(?cap) AS ?capacity) (SAMPLE(?coord) AS ?c) WHERE {{
  SERVICE wikibase:around {{ ?v wdt:P625 ?coord . bd:serviceParam wikibase:center "Point({lon} {lat})"^^geo:wktLiteral ;
                                                    wikibase:radius "{radius}" . }}
  ?v wdt:P1083 ?cap .
  FILTER NOT EXISTS {{ ?v wdt:P576 ?gone }}
  FILTER NOT EXISTS {{ ?v wdt:P3999 ?closed }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}} GROUP BY ?v ?vLabel LIMIT 1000
"""


def sync(db: Database, http: PoliteClient | None, city: CityConfig, now: datetime) -> int:
    row = db.one("SELECT MAX(fetched_at) t FROM venue_refs WHERE city = ?", (city.slug,))
    last = parse_iso(row["t"]) if row and row["t"] else None
    if http is None or (last and now - last < TTL):
        return 0
    lat, lon = city.center
    q = QUERY.format(lat=lat, lon=lon, radius=int(city.radius_km * 1.25))
    try:
        data = http.get_json(
            ENDPOINT,
            params={"query": q, "format": "json"},
            respect_robots=False,
            headers={"Accept": "application/sparql-results+json"},
        )
    except (FetchError, ValueError) as e:
        log.warning("wikidata venue sync failed for %s: %s", city.slug, e)
        return 0
    rows = data.get("results", {}).get("bindings", [])
    with db.tx():
        db.execute("DELETE FROM venue_refs WHERE city = ?", (city.slug,))
        n = 0
        for b in rows:
            try:
                qid = b["v"]["value"].rsplit("/", 1)[-1]
                name = b["vLabel"]["value"]
                cap = int(float(b["capacity"]["value"]))
            except (KeyError, ValueError):
                continue
            if name == qid or cap < 20:
                continue  # unlabeled items / implausible capacities
            coord = (b.get("c") or {}).get("value", "")
            plat = plon = None
            if coord.startswith("Point("):
                xs = coord[6:-1].split()
                plon, plat = float(xs[0]), float(xs[1])
            db.execute(
                "INSERT OR REPLACE INTO venue_refs (city, ref_id, name, capacity, lat, lon, fetched_at) VALUES (?,?,?,?,?,?,?)",
                (city.slug, f"wikidata:{qid}", name, cap, plat, plon, iso(now)),
            )
            n += 1
    return n
