"""Entity resolution: venues, then events. Five sources listing one concert become one canonical event that
keeps every source's price, link and fetch time.

Event matching (all must hold, see ``match_score``):
  * same local calendar day (blocking key — keeps it O(n·k) not O(n²))
  * start times within 3 h (or either side is all-day)
  * same place: same venue entity, or < 400 m apart, or venue names ≥ 0.85 similar
  * titles ≥ 0.82 similar after normalization (strips "presents", "live", years, "tickets"…)
A pair with *no* location data needs titles ≥ 0.95 and starts within 15 min.

Canonical ids are sticky: if any member was already part of an event, the cluster inherits the oldest
such id, so URLs and saved events survive re-runs and new sources joining a cluster.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from gotc.adapters.base import stable_id
from gotc.config import CityConfig
from gotc.pipeline.textnorm import haversine_m, norm_venue, title_similarity, venue_similarity
from gotc.schema import SourceEvent
from gotc.storage.db import Database

# Which source wins a field when members disagree: lower = more trusted. Unlisted sources get 50.
FIELD_TRUST: dict[str, int] = {"curated": 5, "ticketmaster": 10, "seatgeek": 20}


@dataclass
class VenueEntity:
    id: str
    name: str
    norm: str
    lat: float | None = None
    lon: float | None = None
    address: str | None = None
    capacity: int | None = None
    capacity_source: str | None = None
    members: int = 0


@dataclass
class Cluster:
    members: list[SourceEvent] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    venue_id: str | None = None


def trust(source_id: str) -> int:
    base = source_id.split("_")[0]
    return FIELD_TRUST.get(source_id, FIELD_TRUST.get(base, 50))


# ───────────────────────────── venues ─────────────────────────────


def resolve_venues(events: list[SourceEvent], city: CityConfig, known: list[VenueEntity]) -> dict[str, str]:
    """Assign each event (by source key) a venue id. Mutates/extends ``known``."""
    out: dict[str, str] = {}
    by_norm: dict[str, VenueEntity] = {v.norm: v for v in known}
    for ev in sorted(events, key=lambda e: trust(e.source_id)):
        name = ev.location.venue_name
        if not name or len(name) < 3:
            continue
        n = norm_venue(name)
        v = by_norm.get(n)
        if v is None and ev.location.lat is not None and ev.location.lon is not None:
            for cand in known:
                if cand.lat is None or cand.lon is None:
                    continue
                close = haversine_m(ev.location.lat, ev.location.lon, cand.lat, cand.lon) < 150
                if close and venue_similarity(name, cand.name) >= 0.8:
                    v = cand
                    break
        if v is None:
            v = VenueEntity(id=f"ven_{stable_id(city.slug, n)}", name=name, norm=n)
            known.append(v)
            by_norm[n] = v
        if v.lat is None and ev.location.lat is not None:
            v.lat, v.lon = ev.location.lat, ev.location.lon
        v.address = v.address or ev.location.address
        if ev.venue_capacity and not v.capacity:
            v.capacity, v.capacity_source = ev.venue_capacity, ev.source_id
        v.members += 1
        out[_key(ev)] = v.id
    return out


# ───────────────────────────── events ─────────────────────────────


def _key(ev: SourceEvent) -> str:
    return f"{ev.source_id}|{ev.record_id}"


def match_score(a: SourceEvent, b: SourceEvent, va: str | None, vb: str | None) -> float:
    """0 = different events; otherwise a 0.8–1.0 confidence that a and b are the same event."""
    if a.source_id == b.source_id:
        return 0.0  # a source never lists the same event twice under different ids (by assumption)
    dt = abs((a.start - b.start).total_seconds())
    timed = not (a.all_day or b.all_day)
    if timed and dt > 3 * 3600:
        return 0.0
    place: float | None = None
    if va and vb:
        place = 1.0 if va == vb else 0.0
    if (
        a.location.lat is not None
        and b.location.lat is not None
        and a.location.lon is not None
        and b.location.lon is not None
    ):
        d = haversine_m(a.location.lat, a.location.lon, b.location.lat, b.location.lon)
        place = max(place or 0.0, 1.0 if d < 400 else 0.0)
    if a.location.venue_name and b.location.venue_name:
        place = max(
            place or 0.0,
            1.0 if venue_similarity(a.location.venue_name, b.location.venue_name) >= 0.85 else 0.0,
        )
    if place == 0.0:
        return 0.0
    ts = title_similarity(a.title, b.title)
    if place is None:
        if ts >= 0.95 and (not timed or dt <= 900):
            return 0.85
        return 0.0
    if place == 0.0 or ts < 0.82:
        return 0.0
    time_bonus = 0.05 if timed and dt <= 900 else 0.0
    return min(1.0, 0.75 + 0.2 * ts + time_bonus)


def cluster_events(events: list[SourceEvent], venue_of: dict[str, str], tz: str) -> list[Cluster]:
    zone = ZoneInfo(tz)
    parent = list(range(len(events)))
    sources: dict[int, set[str]] = {i: {ev.source_id} for i, ev in enumerate(events)}
    best_score = [1.0] * len(events)

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    blocks: dict[object, list[int]] = defaultdict(list)
    for i, ev in enumerate(events):
        blocks[ev.start.astimezone(zone).date()].append(i)
    for idxs in blocks.values():
        by_source: dict[str, list[int]] = defaultdict(list)
        for i in idxs:
            by_source[events[i].source_id].append(i)
        if len(by_source) < 2:
            continue  # only cross-source pairs can match
        groups_ = list(by_source.values())
        for gi in range(len(groups_)):
            for gj in range(gi + 1, len(groups_)):
                for i in groups_[gi]:
                    for j in groups_[gj]:
                        ri, rj = find(i), find(j)
                        if ri == rj or sources[ri] & sources[rj]:
                            continue  # never merge two records of one source (even transitively)
                        s = match_score(
                            events[i], events[j], venue_of.get(_key(events[i])), venue_of.get(_key(events[j]))
                        )
                        if s > 0:
                            parent[rj] = ri
                            sources[ri] |= sources.pop(rj)
                            best_score[j] = min(best_score[j], s)
    groups: dict[int, Cluster] = defaultdict(Cluster)
    for i, ev in enumerate(events):
        c = groups[find(i)]
        c.members.append(ev)
        c.scores.append(best_score[i])
    for c in groups.values():
        c.members.sort(key=lambda e: (trust(e.source_id), e.source_id))
        vids = [venue_of[_key(m)] for m in c.members if _key(m) in venue_of]
        c.venue_id = vids[0] if vids else None
    return list(groups.values())


def assign_ids(db: Database, city: str, clusters: list[Cluster]) -> list[tuple[str, Cluster]]:
    """Sticky canonical ids: reuse the oldest existing id among members, else mint one."""
    existing: dict[tuple[str, str], tuple[str, str]] = {}
    for r in db.all(
        "SELECT m.source_id, m.record_id, m.event_id, e.first_seen FROM event_members m"
        " JOIN events e ON e.id = m.event_id WHERE m.city = ?",
        (city,),
    ):
        existing[(r["source_id"], r["record_id"])] = (r["event_id"], r["first_seen"])
    used: set[str] = set()
    out: list[tuple[str, Cluster]] = []
    for c in sorted(clusters, key=lambda c: -len(c.members)):  # big clusters claim ids first
        prior = sorted(
            (existing[(m.source_id, m.record_id)] for m in c.members if (m.source_id, m.record_id) in existing),
            key=lambda t: t[1],
        )
        eid = next((p[0] for p in prior if p[0] not in used), None)
        if eid is None:
            anchor = c.members[0]
            eid = f"evt_{stable_id(city, anchor.source_id, anchor.record_id)}"
            if eid in used:
                eid = f"evt_{stable_id(city, *[_key(m) for m in c.members])}"
        used.add(eid)
        out.append((eid, c))
    return out


def first_seen_of(db: Database, city: str, members: list[SourceEvent], now: datetime) -> datetime:
    keys = [(m.source_id, m.record_id) for m in members]
    best = now
    for sid, rid in keys:
        r = db.one(
            "SELECT first_seen FROM source_records WHERE source_id=? AND record_id=? AND city=?",
            (sid, rid, city),
        )
        if r and r["first_seen"]:
            best = min(best, datetime.fromisoformat(r["first_seen"]))
    return best


def same_day_window(start: datetime, tz: str) -> tuple[datetime, datetime]:
    local = start.astimezone(ZoneInfo(tz))
    d0 = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return d0, d0 + timedelta(days=1)
