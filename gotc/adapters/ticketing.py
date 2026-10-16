"""Ticketing APIs: Ticketmaster Discovery v2 (primary/face value) and SeatGeek Platform (resale + stats).

Both need a free key (TICKETMASTER_API_KEY, SEATGEEK_CLIENT_ID). Without one, the unit is reported as
"disabled: needs <KEY>" on the health page — never as a silent gap.

Ticketmaster: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/
  * 5,000 calls/day, 5 req/s; deep paging capped at size*page < 1000 → we page per 2-week window.
SeatGeek: https://platform.seatgeek.com/
  * ``stats.lowest_price``/``listing_count`` are the resale signals we snapshot for price trends.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text, dig, join_address, parse_dt

# Ticketmaster classification → taxonomy. Checked most-specific first: genre, then segment.
TM_GENRES = {
    "Classical": "music.classical",
    "Opera": "music.classical",
    "Comedy": "nightlife.comedy",
    "Theatre": "arts.theater",
    "Dance": "arts.theater",
    "Musical": "arts.theater",
    "Magic & Illusion": "arts.theater",
    "Fine Art": "arts.museum",
    "Children's Theatre": "family.kids",
    "Family": "family.kids",
    "Circus & Specialty Acts": "family.kids",
    "Spectacular": "family.kids",
    "Fairs & Festivals": "community.festival",
    "Hobby/Special Interest Expos": "niche.hobby",
    "Food & Drink": "food_drink.food_festival",
    "Dance/Electronic": "music.dj_night",
    "Film": "arts.film",
}
TM_SEGMENTS = {
    "Music": "music.concert",
    "Sports": "sports_watch.game",
    "Arts & Theatre": "arts.theater",
    "Film": "arts.film",
    "Family": "family.kids",
}
TM_STATUS = {
    "onsale": "on_sale",
    "offsale": "sold_out",
    "canceled": "cancelled",
    "cancelled": "cancelled",
    "postponed": "postponed",
    "rescheduled": "on_sale",
}

SG_TYPES = {
    "concert": "music.concert",
    "music_festival": "music.festival",
    "classical": "music.classical",
    "classical_opera": "music.classical",
    "classical_orchestral_instrumental": "music.classical",
    "comedy": "nightlife.comedy",
    "theater": "arts.theater",
    "broadway_tickets_national": "arts.theater",
    "dance_performance_tour": "arts.theater",
    "family": "family.kids",
    "film": "arts.film",
    "literary": "arts.books",
    "cirque_du_soleil": "family.kids",
}


@register
class TicketmasterAdapter(Adapter):
    name = "ticketmaster"
    respect_robots = False
    BASE = "https://app.ticketmaster.com/discovery/v2/events.json"

    def fetch(self, ctx: FetchContext) -> FetchResult:
        key = ctx.secret("TICKETMASTER_API_KEY")
        p = ctx.params
        lat, lon = ctx.city.center
        horizon = int(p.get("horizon_days", 120))
        window = int(p.get("window_days", 14))
        payloads: list[Payload] = []
        complete = True
        start = ctx.now.replace(microsecond=0)
        for w in range(0, horizon, window):
            w0 = start + timedelta(days=w)
            w1 = start + timedelta(days=min(w + window, horizon))
            for page in range(5):  # 5 × 200 = the 1,000-result deep-paging cap
                q: dict[str, str | int] = {
                    "apikey": key,
                    "latlong": f"{lat},{lon}",
                    "radius": int(p.get("radius_miles", round(ctx.city.radius_km / 1.609))),
                    "unit": "miles",
                    "startDateTime": w0.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "endDateTime": w1.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "size": 200,
                    "page": page,
                    "sort": "date,asc",
                    "countryCode": "US",
                }
                if seg := p.get("segment_id"):
                    q["segmentId"] = seg
                r = ctx.http.get(self.BASE, params=q, respect_robots=False)
                payloads.append(Payload.from_response(r, ctx.now, "json", window=w, page=page))
                info = r.json().get("page", {})
                if page + 1 >= int(info.get("totalPages", 0)):
                    break
            else:
                complete = False
        return FetchResult(payloads, complete=complete)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        data = json.loads(payload.content)
        for ev in dig(data, "_embedded.events", []) or []:
            yield from self._one(ev, ctx)

    def _one(self, ev: dict[str, Any], ctx: ParseContext) -> Iterator[dict[str, Any]]:
        dates = ev.get("dates", {})
        tz = dates.get("timezone") or ctx.city.timezone
        st = dates.get("start", {})
        if st.get("dateTime"):
            start = parse_dt(st["dateTime"], tz)
            if start is not None:
                from zoneinfo import ZoneInfo

                start = start.astimezone(ZoneInfo(tz))
        else:
            start = parse_dt(f"{st.get('localDate', '')} {st.get('localTime', '')}".strip(), tz)
        if not ev.get("name") or start is None:
            yield {"_reject": "missing name/start", "_hint": str(ev.get("id"))}
            return
        venue = (dig(ev, "_embedded.venues", []) or [{}])[0]
        cls = (ev.get("classifications") or [{}])[0]
        genre = dig(cls, "genre.name", "")
        segment = dig(cls, "segment.name", "")
        category = TM_GENRES.get(genre) or TM_SEGMENTS.get(segment)
        if not category:
            category = ctx.tax.classify(ev["name"], genre, segment, default="other.uncategorized").category
        ranges = [r for r in ev.get("priceRanges") or [] if r.get("currency", "USD") == "USD"]
        pmin = min((r["min"] for r in ranges if r.get("min") is not None), default=None)
        pmax = max((r["max"] for r in ranges if r.get("max") is not None), default=None)
        status = TM_STATUS.get(dig(dates, "status.code", ""), "unknown")
        sale_start = parse_dt(dig(ev, "sales.public.startDateTime"), tz)
        if status == "on_sale" and sale_start and sale_start > ctx.fetched_at:
            status = "not_yet_on_sale"
        lat = _f(dig(venue, "location.latitude"))
        lon = _f(dig(venue, "location.longitude"))
        url = ev.get("url")
        offers = []
        if url:
            offers.append(
                {
                    "seller": "Ticketmaster",
                    "kind": "primary",
                    "url": url,
                    "price_min": pmin,
                    "price_max": pmax,
                    "availability": status,
                    "fees_included": False,
                    "source_id": ctx.source.id,
                    "fetched_at": ctx.fetched_at,
                }
            )
        yield ctx.base(
            str(ev["id"]),
            title=clean_text(ev["name"], 300),
            description=clean_text(ev.get("info") or ev.get("pleaseNote"), 2000),
            url=url,
            category=category,
            source_categories=[s for s in (segment, genre, dig(cls, "subGenre.name", "")) if s],
            start=start,
            all_day=not st.get("dateTime") and not st.get("localTime"),
            location={
                "venue_name": venue.get("name"),
                "address": join_address(
                    dig(venue, "address.line1"),
                    dig(venue, "city.name"),
                    f"{dig(venue, 'state.stateCode', '')} {venue.get('postalCode', '')}".strip(),
                ),
                "lat": lat if lon is not None else None,
                "lon": lon if lat is not None else None,
                "geocode_method": "reported" if lat is not None and lon is not None else None,
            },
            organizer=dig(ev, "promoter.name"),
            price={"min": pmin, "max": pmax, "note": "face value, before fees"} if pmin is not None else {},
            offers=offers,
            availability=status,
            extras={
                "tm_venue_id": venue.get("id"),
                "ticket_limit": dig(ev, "ticketLimit.info"),
                "onsale_at": dig(ev, "sales.public.startDateTime"),
                "image": _best_image(ev.get("images") or []),
            },
        )


@register
class SeatGeekAdapter(Adapter):
    name = "seatgeek"
    respect_robots = False
    BASE = "https://api.seatgeek.com/2/events"

    def fetch(self, ctx: FetchContext) -> FetchResult:
        cid = ctx.secret("SEATGEEK_CLIENT_ID")
        p = ctx.params
        lat, lon = ctx.city.center
        payloads: list[Payload] = []
        complete = True
        until = ctx.now + timedelta(days=int(p.get("horizon_days", 120)))
        for page in range(1, int(p.get("max_pages", 20)) + 1):
            q: dict[str, str | int | float] = {
                "client_id": cid,
                "lat": lat,
                "lon": lon,
                "range": f"{p.get('radius_miles', round(ctx.city.radius_km / 1.609))}mi",
                "per_page": 100,
                "page": page,
                "sort": "datetime_utc.asc",
                "datetime_utc.gte": ctx.now.strftime("%Y-%m-%dT%H:%M:%S"),
                "datetime_utc.lte": until.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            r = ctx.http.get(self.BASE, params=q, respect_robots=False)
            payloads.append(Payload.from_response(r, ctx.now, "json", page=page))
            meta = r.json().get("meta", {})
            if page * int(meta.get("per_page", 100)) >= int(meta.get("total", 0)):
                break
        else:
            complete = False
        return FetchResult(payloads, complete=complete)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        for ev in json.loads(payload.content).get("events", []):
            venue = ev.get("venue") or {}
            tz = venue.get("timezone") or ctx.city.timezone
            start = parse_dt(ev.get("datetime_local"), tz)
            if not ev.get("title") or start is None:
                yield {"_reject": "missing title/start", "_hint": str(ev.get("id"))}
                continue
            stats = ev.get("stats") or {}
            listing_count = stats.get("listing_count")
            lowest = stats.get("lowest_price")
            highest = stats.get("highest_price")
            category = SG_TYPES.get(ev.get("type", ""))
            if not category:
                taxo = [t.get("name", "") for t in ev.get("taxonomies") or []]
                if any(t in ("sports", "nba", "nfl", "mlb", "nhl", "mls", "ncaa_football") for t in taxo):
                    category = "sports_watch.game"
                else:
                    category = ctx.tax.classify(ev["title"], " ".join(taxo), default="other.uncategorized").category
            avail = "unknown"
            if listing_count == 0:
                avail = "sold_out"
            elif listing_count:
                avail = "on_sale"
            cap = venue.get("capacity") or None
            loc = venue.get("location") or {}
            yield ctx.base(
                str(ev["id"]),
                title=clean_text(ev["title"], 300),
                url=ev.get("url"),
                category=category,
                source_categories=[ev.get("type", "")] + [t.get("name", "") for t in ev.get("taxonomies") or []],
                start=start,
                all_day=bool(ev.get("datetime_tbd") or ev.get("time_tbd")),
                location={
                    "venue_name": venue.get("name"),
                    "address": join_address(venue.get("address"), venue.get("extended_address")),
                    "lat": _f(loc.get("lat")),
                    "lon": _f(loc.get("lon")),
                    "geocode_method": "reported" if loc.get("lat") else None,
                },
                price={"min": lowest, "max": highest, "note": "resale, lowest listing"} if lowest else {},
                offers=[
                    {
                        "seller": "SeatGeek",
                        "kind": "resale",
                        "url": ev["url"],
                        "price_min": lowest,
                        "price_max": highest,
                        "listing_count": listing_count,
                        "availability": avail,
                        "fees_included": False,
                        "source_id": ctx.source.id,
                        "fetched_at": ctx.fetched_at,
                    }
                ]
                if ev.get("url")
                else [],
                availability=avail,
                venue_capacity=int(cap) if cap else None,
                extras={
                    "sg_score": ev.get("score"),
                    "sg_popularity": ev.get("popularity"),
                    "sg_avg_price": stats.get("average_price"),
                    "sg_median_price": stats.get("median_price"),
                    "sg_visible_listings": stats.get("visible_listing_count"),
                    "performer": ((ev.get("performers") or [{}])[0]).get("name"),
                },
            )


def _f(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _best_image(images: list[dict[str, Any]]) -> str | None:
    good = [i for i in images if i.get("ratio") == "16_9" and int(i.get("width") or 0) >= 640]
    good.sort(key=lambda i: int(i.get("width") or 0))
    return good[0]["url"] if good else None
