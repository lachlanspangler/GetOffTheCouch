"""Which venues keep events off the map? Lists the most common venue names / addresses among a city's exported
events that have no coordinates, so curators know what to add to config/venues/<slug>.yaml.
   python scripts/venue_gaps.py <slug> [--top 30]"""

import argparse
import json
from collections import Counter
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("slug")
ap.add_argument("--top", type=int, default=30)
a = ap.parse_args()
feed = json.loads(Path(f"web/public/data/cities/{a.slug}.json").read_text())
evs = [e for e in feed["events"] if e.get("kind") != "opening"]
missing = [e for e in evs if e["location"].get("lat") is None]
c: Counter[str] = Counter()
src: dict[str, set[str]] = {}
for e in missing:
    loc = e["location"]
    key = f"{loc.get('venue_name') or ''} | {loc.get('address') or ''}".strip(" |") or "(no location at all)"
    c[key] += 1
    src.setdefault(key, set()).add(e["sources"][0]["source_id"])
print(
    f"{a.slug}: {len(missing)} of {len(evs)} events have no coordinates ({100 * (1 - len(missing) / max(1, len(evs))):.0f}% placed)"
)
for k, n in c.most_common(a.top):
    print(f"{n:5}  {k[:90]}   [{', '.join(sorted(src[k]))[:60]}]")
