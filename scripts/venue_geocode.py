"""Fill lat/lon for curated venues that have an `address` but no coordinates, using the U.S. Census geocoder
(public, keyless, built for this). Records how the point was derived. Never touches entries that already have
coordinates.   python scripts/venue_geocode.py <slug>"""

import sys
import time
from pathlib import Path

import httpx
import yaml

UA = "GetOffTheCouch/0.1 (+https://github.com/lachlanspangler/GetOffTheCouch)"
URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
path = Path(f"config/venues/{sys.argv[1]}.yaml")
items = yaml.safe_load(path.read_text()) or []
done = 0
with httpx.Client(headers={"User-Agent": UA}, timeout=30) as c:
    for it in items:
        if it.get("lat") is not None or not it.get("address"):
            continue
        try:
            r = c.get(URL, params={"address": it["address"], "benchmark": "Public_AR_Current", "format": "json"})
            m = (r.json().get("result") or {}).get("addressMatches") or []
        except (httpx.HTTPError, ValueError) as e:  # Census sometimes answers with an HTML error page: skip, rerun later
            print(f"Census error (retry later): {it['name']}: {type(e).__name__}")
            time.sleep(5.0)
            continue
        if m:
            it["lat"], it["lon"] = round(m[0]["coordinates"]["y"], 6), round(m[0]["coordinates"]["x"], 6)
            it["coords_source"] = f"U.S. Census geocoder: {m[0]['matchedAddress']}"
            done += 1
        else:
            print(f"no Census match: {it['name']} — {it['address']}")
        time.sleep(2.0)
head = "".join(line for line in path.read_text().splitlines(keepends=True) if line.startswith("#"))
path.write_text(head + yaml.safe_dump(items, sort_keys=False, allow_unicode=True, width=120))
print(f"{path}: geocoded {done}")
