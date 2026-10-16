"""Build: source_records → canonical, enriched events (per city). Pure re-derivation, safe to re-run.

  load live records → geocode → resolve venues → cluster → merge → deadlines → enrich → store

The events table is a *snapshot*: each build replaces the city's events wholesale, so a bad build is
fixed by fixing the code and building again. History lives in source_records / price_snapshots / raw.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from gotc.adapters.base import stable_id
from gotc.config import CityConfig, Registry
from gotc.pipeline.deadlines import extract_deadlines
from gotc.pipeline.enrich import derive_tags, estimate_attendance, social_score, ticket_signal
from gotc.pipeline.geocode import Geocoder
from gotc.pipeline.resolve import (
    Cluster,
    VenueEntity,
    assign_ids,
    cluster_events,
    first_seen_of,
    resolve_venues,
)
from gotc.pipeline.textnorm import norm_venue
from gotc.schema import (
    Availability,
    Event,
    EventKind,
    FieldProvenance,
    Location,
    Method,
    Offer,
    Price,
    Registration,
    SourceEvent,
    SourceRef,
    TicketSignal,
    Venue,
)
from gotc.settings import CONFIG_DIR
from gotc.storage.db import Database, iso
from gotc.taxonomy import FALLBACK, Taxonomy, taxonomy

log = logging.getLogger(__name__)


OPENING_WINDOW_DAYS = 60  # a new license is 'news' for about two months (I-059)


@dataclass
class BuildStats:
    city: str
    records: int = 0
    events: int = 0
    merged: int = 0
    geocoded: int = 0
    venues: int = 0
    deadlines_extracted: int = 0
    stale: int = 0
    weather: int = 0
    outside: int = 0


def load_live_records(db: Database, city: str, now: datetime, reg: Registry | None = None) -> list[SourceEvent]:
    rows = db.all(
        "SELECT data, unit, first_seen FROM source_records WHERE city = ? AND gone_at IS NULL AND start_at >= ?",
        (city, iso(now - timedelta(days=4000))),
    )
    by_first_seen = _first_seen_opening_units(reg) if reg else set()
    baselines: dict[str, datetime] = {}
    out: list[SourceEvent] = []
    for r in rows:
        ev = SourceEvent.model_validate_json(r["data"])
        if r["unit"] in by_first_seen:
            # I-058: datasets with no original-issue date (e.g. Minneapolis On_Sale_Liquor). A license is "new"
            # only if it appeared after our first snapshot; its date is the day we first saw it (labeled).
            if r["unit"] not in baselines:
                b = db.one("SELECT MIN(first_seen) t FROM source_records WHERE unit = ?", (r["unit"],))
                baselines[r["unit"]] = datetime.fromisoformat(b["t"]) if b and b["t"] else now
            seen = datetime.fromisoformat(r["first_seen"])
            if seen < baselines[r["unit"]] + timedelta(hours=6):
                continue  # part of the initial backfill: an existing business, not news
            local = seen.astimezone(ZoneInfo(ev.timezone))
            ev.start = datetime.combine(local.date(), time(0, 0), ZoneInfo(ev.timezone))
            ev.all_day, ev.kind = True, EventKind.OPENING
            ev.description = (
                ev.description or ""
            ) + f"\n\nFirst appeared in the city's license data on {local:%b %-d, %Y}."
        if ev.start < now - timedelta(days=200) and ev.kind != EventKind.OPENING:
            continue
        end = ev.end or ev.start + timedelta(hours=3)
        closes = ev.registration.closes_at if ev.registration else None
        recent_opening = ev.kind == EventKind.OPENING and ev.start >= now - timedelta(days=OPENING_WINDOW_DAYS)
        if end >= now - timedelta(hours=2) or (closes and closes >= now) or recent_opening:
            out.append(ev)
    return out


def _first_seen_opening_units(reg: Registry) -> set[str]:
    return {u.key for u in reg.units() if u.source.params.get("openings_by_first_seen")}


def load_curated_venues(city: str, config_dir: Path = CONFIG_DIR) -> list[VenueEntity]:
    path = config_dir / "venues" / f"{city}.yaml"
    if not path.exists():
        return []
    items = yaml.safe_load(path.read_text()) or []
    out: list[VenueEntity] = []
    from gotc.adapters.base import stable_id

    for it in items:
        names = [it["name"], *it.get("aliases", [])]
        base = VenueEntity(
            id=f"ven_{stable_id(city, norm_venue(it['name']))}",
            name=it["name"],
            norm=norm_venue(it["name"]),
            lat=it.get("lat"),
            lon=it.get("lon"),
            address=it.get("address"),
            capacity=it.get("capacity"),
            capacity_source=it.get("capacity_source"),
        )
        out.append(base)
        for alias in names[1:]:
            out.append(VenueEntity(**{**base.__dict__, "norm": norm_venue(alias), "members": 0}))
    return out


def build_city(
    db: Database,
    reg: Registry,
    city: CityConfig,
    now: datetime,
    geocoder: Geocoder | None = None,
    tax: Taxonomy | None = None,
) -> BuildStats:
    tax = tax or taxonomy()
    stats = BuildStats(city.slug)
    records = load_live_records(db, city.slug, now, reg)
    stats.records = len(records)

    if geocoder:
        geocoder.lookups = 0  # the live-lookup budget is per city, so early cities can't starve later ones
        stats.geocoded += geocoder.batch(
            [r.location.address for r in records if r.location.lat is None and r.location.address], city
        )
        for rec in records:
            if rec.location.lat is None and (rec.location.address or rec.location.venue_name):
                q = rec.location.address or rec.location.venue_name or ""
                res = geocoder.geocode(q, city)
                if res:
                    rec.location.lat, rec.location.lon = res.lat, res.lon
                    rec.location.geocode_method = Method.DERIVED
                    rec.location.geocode_confidence = res.confidence
                    stats.geocoded += 1

    fallbacks = {u.source.id: u.source.params["fallback_point"] for u in reg.units(city=city.slug)
                 if u.source.params.get("fallback_point")}
    for rec in records:
        fp = fallbacks.get(rec.source_id)
        if fp and rec.location.lat is None:
            # an institution's room we can't map ("FAC 2.134"): pin to the campus, clearly approximate
            rec.location.lat, rec.location.lon = float(fp["lat"]), float(fp["lon"])
            rec.location.geocode_method = Method.DERIVED
            rec.location.geocode_confidence = 0.3
            label = fp.get("label", "on campus")
            rec.location.address = f"{rec.location.address or rec.location.venue_name or ''} (approximate: {label})".strip()

    from gotc.pipeline.textnorm import haversine_m

    fence_m = city.radius_km * 1000 * 2.5
    kept = [
        r
        for r in records
        if r.location.lat is None
        or r.location.lon is None
        or haversine_m(r.location.lat, r.location.lon, *city.center) <= fence_m
    ]
    stats.outside = len(records) - len(kept)
    records = kept

    venues = load_curated_venues(city.slug)
    if geocoder is not None:
        from gotc.pipeline.venue_refs import sync

        sync(db, None if geocoder.offline else geocoder.http, city, now)
    venues += [
        VenueEntity(
            f"ven_{stable_id(city.slug, norm_venue(r['name']))}",
            r["name"],
            norm_venue(r["name"]),
            r["lat"],
            r["lon"],
            None,
            r["capacity"],
            r["ref_id"],
        )
        for r in db.all("SELECT * FROM venue_refs WHERE city = ?", (city.slug,))
    ]
    venues += [
        VenueEntity(
            r["id"],
            r["name"],
            r["norm_name"],
            r["lat"],
            r["lon"],
            r["address"],
            r["capacity"],
            r["capacity_source"],
        )
        for r in db.all("SELECT * FROM venues WHERE city = ?", (city.slug,))
        if not any(v.id == r["id"] for v in venues)
    ]
    venue_of = resolve_venues(records, city, venues)
    clusters = cluster_events(records, venue_of, city.timezone)
    ided = assign_ids(db, city.slug, clusters)
    venue_by_id = {v.id: v for v in venues}

    merged = [(merge(eid, cl, city, now, tax, db, reg), cl) for eid, cl in ided]
    baselines = {
        r["source_id"]: datetime.fromisoformat(r["t"])
        for r in db.all(
            "SELECT source_id, MIN(first_seen) t FROM source_records WHERE city = ? GROUP BY source_id", (city.slug,)
        )
    }
    for ev, _ in merged:
        base = min((baselines[s.source_id] for s in ev.sources if s.source_id in baselines), default=now)
        ev.is_new = ev.first_seen >= base + timedelta(hours=6) and now - ev.first_seen < timedelta(hours=72)
    assign_series([ev for ev, _ in merged], now)

    events: list[tuple[Event, Cluster]] = []
    for ev, cl in merged:
        v = venue_by_id.get(cl.venue_id or "")
        if v is not None:
            ev.venue_id = v.id
        snaps = _snapshots(db, city.slug, cl.members)
        ev.tickets, ev.price_trend = ticket_signal(ev, snaps, now)
        reported = next((m.reported_attendance for m in cl.members if m.reported_attendance), None)
        ev.attendance = estimate_attendance(
            ev, tax, v.capacity if v else None, v.capacity_source if v else None, reported
        )
        apply_spots(ev, cl.members)
        text = " ".join(filter(None, [ev.title, *(m.description or "" for m in cl.members)]))
        ev.tags = derive_tags(ev, text, tax)
        ev.social = social_score(ev, tax)
        if ev.registration and ev.registration.method == Method.EXTRACTED:
            stats.deadlines_extracted += 1
        stats.merged += len(cl.members) - 1
        stats.stale += int(ev.stale)
        events.append((ev, cl))

    if geocoder is not None:
        from gotc.pipeline.weather import attach, hourly

        periods, wx_at = hourly(db, geocoder.http if not geocoder.offline else None, city, now)
        stats.weather = attach([ev for ev, _ in events], periods, wx_at, tax)

    with db.tx():
        db.execute("DELETE FROM event_members WHERE city = ?", (city.slug,))
        db.execute("DELETE FROM events WHERE city = ?", (city.slug,))
        for ev, cl in events:
            db.execute(
                "INSERT INTO events (id, city, data, start_at, category, first_seen, updated_at) VALUES (?,?,?,?,?,?,?)",
                (
                    ev.id,
                    city.slug,
                    ev.model_dump_json(),
                    iso(ev.start),
                    ev.category,
                    iso(ev.first_seen),
                    iso(now),
                ),
            )
            for m, score in zip(cl.members, cl.scores, strict=True):
                db.execute(
                    "INSERT OR REPLACE INTO event_members (event_id, source_id, record_id, city, match_score)"
                    " VALUES (?,?,?,?,?)",
                    (ev.id, m.source_id, m.record_id, city.slug, score),
                )
        used = {cl.venue_id for _, cl in events if cl.venue_id}
        for v in venues:
            if v.id in used:
                db.execute(
                    "INSERT INTO venues (id, city, name, norm_name, address, lat, lon, capacity, capacity_source,"
                    " updated_at) VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET"
                    " lat=COALESCE(venues.lat, excluded.lat), lon=COALESCE(venues.lon, excluded.lon),"
                    " address=COALESCE(venues.address, excluded.address),"
                    " capacity=COALESCE(excluded.capacity, venues.capacity),"
                    " capacity_source=COALESCE(excluded.capacity_source, venues.capacity_source),"
                    " updated_at=excluded.updated_at",
                    (
                        v.id,
                        city.slug,
                        v.name,
                        v.norm,
                        v.address,
                        v.lat,
                        v.lon,
                        v.capacity,
                        v.capacity_source,
                        iso(now),
                    ),
                )
                used.discard(v.id)  # aliases share an id; write once
        stats.venues = len({cl.venue_id for _, cl in events if cl.venue_id})
    stats.events = len(events)
    return stats


def apply_spots(ev: Event, members: list[SourceEvent]) -> None:
    """Registration counts reported by the source (e.g. library programs: 15 of 20 spots taken).

    This is the one *real* "% left" signal we have — reported, not estimated — so it overrides the
    listing-based guess and gives an attendance band anchored on actual signups.
    """
    from gotc.pipeline.enrich import sig2
    from gotc.schema import Estimate

    src = next((m for m in members if m.extras.get("capacity") and m.extras.get("registered") is not None), None)
    only_left = next((m for m in members if m.extras.get("spots_left") is not None), None)
    if src is None and only_left is not None:  # e.g. volunteer shifts: "3 volunteers still needed"
        n = int(str(only_left.extras["spots_left"]))
        ev.tickets.spots_left = n
        if 0 < n <= 2:
            ev.tickets.selling_fast = True
            ev.tickets.signal = f"only {n} spot{'s' if n != 1 else ''} left"
        return
    if src is None:
        if "registration_required" in ev.tags and ev.registration is None:
            ev.registration = Registration(
                closes_at=ev.start,
                method=Method.DERIVED,
                confidence=0.5,
                evidence="Registration required; no separate deadline is published, so sign up before it starts.",
            )
        return
    cap = int(str(src.extras["capacity"]))
    reg = min(int(str(src.extras["registered"])), cap)
    left = max(0.0, (cap - reg) / cap * 100)
    ev.tickets.spots_left, ev.tickets.spots_total = cap - reg, cap
    ev.tickets.pct_left = Estimate(
        low=round(left),
        mid=round(left),
        high=round(left),
        method=f"{reg} of {cap} spots taken (reported by {src.source_id})",
        inputs={"capacity": cap, "registered": reg},
        confidence=0.9,
    )
    if left == 0:
        ev.tickets.availability = Availability.REGISTRATION_CLOSED
    elif left <= 20:
        ev.tickets.selling_fast = True
        ev.tickets.signal = f"only {cap - reg} of {cap} spots left"
    ev.attendance = Estimate(
        low=min(sig2(max(1, reg * 0.75)), cap),
        mid=max(1, reg),
        high=cap,
        method=f"{reg} registered so far, capacity {cap} (reported)",
        inputs={"registered": reg, "capacity": cap},
        confidence=0.7,
    )
    if ev.registration is None:
        ev.registration = Registration(
            closes_at=ev.start,
            method=Method.DERIVED,
            confidence=0.5,
            evidence=f"Registration required ({reg} of {cap} spots taken); no separate deadline is published.",
        )


def assign_series(events: list[Event], now: datetime) -> None:
    """Occurrences of one repeating thing share a series id (I-014); the list shows one card per series.

    Key = (source, normalized title, place). A program that runs at ≥3 different places under one title
    (e.g. "Street Health Outreach" at 20 sites) is one series regardless of place.
    """
    from gotc.adapters.base import stable_id
    from gotc.pipeline.textnorm import norm_title

    def place(ev: Event) -> str:
        return ev.venue_id or norm_venue(ev.location.address) or ""

    by_title: dict[tuple[str, str], list[Event]] = {}
    for ev in events:
        by_title.setdefault((ev.sources[0].source_id, norm_title(ev.title)), []).append(ev)
    groups: dict[tuple[str, str, str], list[Event]] = {}
    for (src, title), evs in by_title.items():
        multi_site = len({place(e) for e in evs}) >= 3
        for ev in evs:
            groups.setdefault((src, title, "*" if multi_site else place(ev)), []).append(ev)
    for key, evs in groups.items():
        if len(evs) < 2:
            continue
        sid = f"ser_{stable_id(*key)}"
        dates = sorted({e.start for e in evs if (e.end or e.start) >= now - timedelta(hours=2)})[:8]
        for e in evs:
            e.series_id = sid
            e.series_dates = dates
            if len(evs) >= 3 and e.kind == EventKind.ONE_OFF:
                e.kind = EventKind.RECURRING


def merge(eid: str, cl: Cluster, city: CityConfig, now: datetime, tax: Taxonomy, db: Database, reg: Registry) -> Event:
    ms = cl.members
    primary = ms[0]

    def prov(
        src: SourceEvent, method: Method = Method.REPORTED, conf: float = 1.0, note: str | None = None
    ) -> FieldProvenance:
        return FieldProvenance(
            source=src.source_id, fetched_at=src.fetched_at, method=method, confidence=conf, note=note
        )

    cat_src = next((m for m in ms if m.category != FALLBACK), primary)
    loc_src = (
        next((m for m in ms if m.location.lat is not None and m.location.venue_name), None)
        or next((m for m in ms if m.location.lat is not None), None)
        or next((m for m in ms if m.location.address), primary)
    )
    desc = max((m.description or "" for m in ms), key=len) or None

    offers: dict[tuple[str, str], Offer] = {}
    for m in ms:
        for o in m.offers:
            offers.setdefault((o.seller, str(o.url)), o)
    mins = [x for m in ms for x in [m.price.min, *(o.price_min for o in m.offers)] if x is not None]
    maxs = [x for m in ms for x in [m.price.max, *(o.price_max for o in m.offers)] if x is not None]
    is_free = any(m.price.is_free for m in ms) and not mins
    notes = [m.price.note for m in ms if m.price.note]
    price = Price(
        min=min(mins) if mins else None,
        max=max(maxs) if maxs else None,
        is_free=is_free,
        note=notes[0] if notes else None,
    )

    registration = next((m.registration for m in ms if m.registration and m.registration.closes_at), None) or next(
        (m.registration for m in ms if m.registration), None
    )
    reg_prov: FieldProvenance | None = None
    if registration is not None:
        reg_src = next(m for m in ms if m.registration is registration)
        reg_prov = prov(reg_src, registration.method, registration.confidence)
    if registration is None or registration.closes_at is None:
        found = []
        for m in ms:
            found = extract_deadlines(m.description, city.timezone, now, m.start)
            if found:
                src = m
                break
        if found:
            kw: dict[str, Any] = {d.field: d.at for d in found}
            evidence = " / ".join(d.evidence for d in found)
            base = registration.model_dump() if registration else {}
            base.update(kw)
            base.update({"evidence": evidence, "method": Method.EXTRACTED, "confidence": 0.65})
            registration = Registration.model_validate(base)
            reg_prov = prov(src, Method.EXTRACTED, 0.65, note=evidence[:200])

    location = Location.model_validate(loc_src.location.model_dump())
    kind = EventKind.SEASON if any(m.kind == EventKind.SEASON for m in ms) else primary.kind

    freshest = max(ms, key=lambda m: m.fetched_at)
    stale_reason = None
    sla = (
        timedelta(hours=reg.sla_hours(reg.all_sources()[freshest.source_id]))
        if freshest.source_id in reg.all_sources()
        else timedelta(days=7)
    )
    stale = now - freshest.fetched_at > sla
    if stale:
        age_h = (now - freshest.fetched_at).total_seconds() / 3600
        stale_reason = (
            f"last confirmed {age_h:.0f}h ago by {freshest.source_id} (freshness SLA {sla.total_seconds() / 3600:.0f}h)"
        )

    provenance = {
        "title": prov(primary),
        "start": prov(primary),
        "category": prov(cat_src, Method.REPORTED if cat_src.source_categories else Method.DERIVED, 0.8),
        "location": prov(
            loc_src,
            loc_src.location.geocode_method or Method.REPORTED,
            loc_src.location.geocode_confidence or 1.0,
        ),
    }
    if mins:
        price_src = next(
            (m for m in ms if m.price.min is not None or any(o.price_min is not None for o in m.offers)),
            primary,
        )
        provenance["price"] = prov(price_src)
    if reg_prov:
        provenance["registration"] = reg_prov

    return Event(
        id=eid,
        city=city.slug,
        title=primary.title,
        summary=(desc[:600] + ("…" if len(desc) > 600 else "")) if desc else None,
        url=primary.url or next((m.url for m in ms if m.url), None),
        kind=kind,
        category=cat_src.category,
        categories=list(dict.fromkeys(m.category for m in ms)),
        tags=sorted({t for m in ms for t in m.tags}),
        start=primary.start,
        end=primary.end or next((m.end for m in ms if m.end), None),
        all_day=all(m.all_day for m in ms),
        timezone=city.timezone,
        recurrence=next((m.recurrence for m in ms if m.recurrence), None),
        location=location,
        organizer=next((m.organizer for m in ms if m.organizer), None),
        price=price,
        offers=sorted(
            offers.values(),
            key=lambda o: (o.kind != "primary", o.price_min if o.price_min is not None else 1e9),
        ),
        registration=registration,
        tickets=TicketSignal(availability=_availability(ms)),
        sources=[
            SourceRef(source_id=m.source_id, record_id=m.record_id, url=m.url, fetched_at=m.fetched_at) for m in ms
        ],
        provenance=provenance,
        first_seen=first_seen_of(db, city.slug, ms, now),
        last_checked=freshest.fetched_at,
        stale=stale,
        stale_reason=stale_reason,
        is_demo=any(m.is_demo for m in ms),
    )


def _availability(ms: list[SourceEvent]) -> Availability:
    known = [m.availability for m in ms if m.availability != Availability.UNKNOWN]
    return known[0] if known else Availability.UNKNOWN


def _snapshots(db: Database, city: str, members: list[SourceEvent]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for m in members:
        rows = db.all(
            "SELECT seller, observed_at, price_min, price_max, listing_count, availability FROM price_snapshots"
            " WHERE source_id=? AND record_id=? AND city=? ORDER BY observed_at DESC LIMIT 200",
            (m.source_id, m.record_id, city),
        )
        out.extend(dict(r) for r in rows)
    return out


def venues_for_export(db: Database, city: str) -> list[Venue]:
    return [
        Venue(
            id=r["id"],
            name=r["name"],
            address=r["address"],
            lat=r["lat"],
            lon=r["lon"],
            capacity=r["capacity"],
            capacity_source=r["capacity_source"],
        )
        for r in db.all("SELECT * FROM venues WHERE city = ?", (city,))
    ]


def dump(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str)
