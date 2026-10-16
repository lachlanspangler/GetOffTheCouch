"""Reference venue capacities (Wikidata P1083 "maximum capacity") — **live sync disabled 2026-10-16**.

Why disabled: ``query.wikidata.org/robots.txt`` is ``User-agent: *`` / ``Disallow: /sparql`` (and
``/bigdata``), and the allowed-looking alternatives are disallowed too: ``www.wikidata.org/robots.txt``
disallows ``/w/`` (so ``/w/api.php`` wbsearchentities/wbgetentities), ``/api/`` and ``/wiki/Special:``
(so ``Special:EntityData``). Both were re-read with our UA on 2026-10-16. Our rule is "if robots disallows
us, disable the source; never work around it", so nothing here touches the network any more.

What still works:
  * curated capacities in ``config/venues/<slug>.yaml`` (each with a ``capacity_source`` URL) — the primary path
  * rows already in ``venue_refs`` (fetched before 2026-10-16; Wikidata data is CC0) keep serving with their
    QID as the source, and are never refreshed. ``store_bindings`` is kept so a future allowed bulk path
    (e.g. an operator-imported dump extract) can reuse the same validation.

See docs/SOURCES.md "Robots exceptions and API usage policies".
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from gotc.config import CityConfig
from gotc.http.client import PoliteClient
from gotc.storage.db import Database, iso

log = logging.getLogger(__name__)
LIVE_SYNC = False  # robots.txt disallows every Wikidata query path for crawlers (see module docstring)
DISABLED_REASON = "query.wikidata.org robots.txt disallows /sparql; www.wikidata.org disallows /w/ and /api/"


def sync(db: Database, http: PoliteClient | None, city: CityConfig, now: datetime) -> int:
    """No-op (returns 0): the live Wikidata sync is disabled. Existing rows are left untouched."""
    if http is not None and not LIVE_SYNC:
        log.debug("wikidata venue sync disabled for %s: %s", city.slug, DISABLED_REASON)
    return 0


def store_bindings(db: Database, city: CityConfig, data: dict[str, Any], now: datetime) -> int:
    """Replace a city's reference venues from SPARQL-JSON-shaped bindings (v, vLabel, capacity, c).

    Unlabeled items and implausible capacities (< 20) are dropped. Returns rows stored.
    """
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
                continue
            coord = (b.get("c") or {}).get("value", "")
            plat = plon = None
            if coord.startswith("Point("):
                xs = coord[6:-1].split()
                plon, plat = float(xs[0]), float(xs[1])
            db.execute(
                "INSERT OR REPLACE INTO venue_refs (city, ref_id, name, capacity, lat, lon, fetched_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (city.slug, f"wikidata:{qid}", name, cap, plat, plon, iso(now)),
            )
            n += 1
    return n
