"""schema.org JSON-LD events embedded in ordinary web pages — the keyless way into venues' own calendars.

Most venue/promoter sites (WordPress event plugins, Squarespace, Etix/Tixr/SeeTickets/DICE venue pages,
ticketing white-labels) embed ``<script type="application/ld+json">`` blocks for search engines. Those blocks
carry the facts we want, in a standard vocabulary: name, start/end with offsets, venue + address + geo,
face-value offers (price / AggregateOffer low–high, availability, on-sale ``validFrom``), performers, status.

    params:
      urls: [https://venue.example/calendar/, https://venue.example/calendar/page/2/]   # listing page(s)
      follow: '/event/[^/?#]+/?$'     # optional regex: detail links on the listing pages to fetch too
      max_follow: 30                  # cap on detail pages per run (the run is marked incomplete if hit)
      horizon_days: 180               # events starting further out are ignored
      venue: {name: First Avenue, address: "701 N 1st Ave, Minneapolis, MN 55403"}   # fallback location
      default_category: music.concert # for plain ``Event`` records that classify as nothing
      category_map: {Comedy: nightlife.comedy}   # @type or keyword (in the title) → taxonomy id
      organizer: First Avenue Productions
      zero_is_free: false             # treat an offer price of 0 as "free" (many sites use 0 for "unknown")
      trust_valid_from: true          # false when offers.validFrom is a placeholder (e.g. = the event date)
      date_only: false                # true when the source's clock times are wrong: keep dates (all-day)
      tags: [indoor]

Fetch is network only (listing pages, then up to ``max_follow`` detail pages at ``min_interval_s`` ≥ 2 s,
robots.txt honored by ``PoliteClient``). Detail payloads are returned *before* listing payloads, so when a
listing and a detail page describe the same event (same url/@id + start) the richer detail record wins the
ingest de-duplication. Parse is pure: every Event-typed node in every block (``@graph``, arrays,
``ItemList.itemListElement``, nested ``subEvent``) becomes one record; past/out-of-horizon events are
windowed out like the ICS adapter does; unusable events are yielded as ``_reject`` records.
"""

from __future__ import annotations

import html as htmllib
import json
import re
from collections.abc import Iterator
from datetime import datetime, time, timedelta
from typing import Any
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register, stable_id
from gotc.adapters.common import clean_text, join_address, money, parse_dt, prices_in_text, says_free
from gotc.http.client import FetchError

EVENT_TYPES = {
    "Event",
    "MusicEvent",
    "ComedyEvent",
    "TheaterEvent",
    "DanceEvent",
    "SocialEvent",
    "SportsEvent",
    "Festival",
    "LiteraryEvent",
    "ScreeningEvent",
    "ExhibitionEvent",
    "EducationEvent",
    "FoodEvent",
    "BusinessEvent",
    "ChildrensEvent",
    "VisualArtsEvent",
    "SaleEvent",
    "CourseInstance",
    "EventSeries",
}
# @type → taxonomy id when the title doesn't classify more specifically
TYPE_CATEGORY = {
    "MusicEvent": "music.concert",
    "ComedyEvent": "nightlife.comedy",
    "TheaterEvent": "arts.theater",
    "DanceEvent": "arts.theater",
    "ScreeningEvent": "arts.film",
    "ExhibitionEvent": "arts.museum",
    "VisualArtsEvent": "arts.museum",
    "LiteraryEvent": "arts.books",
    "SportsEvent": "sports_watch.game",
    "ChildrensEvent": "family.kids",
}
AVAILABILITY = {
    "instock": "on_sale",
    "onlineonly": "on_sale",
    "instoreonly": "on_sale",
    "limitedavailability": "limited",
    "soldout": "sold_out",
    "outofstock": "sold_out",
    "preorder": "not_yet_on_sale",
    "presale": "not_yet_on_sale",
    "backorder": "waitlist",
}
_AVAIL_RANK = ["on_sale", "limited", "waitlist", "not_yet_on_sale", "sold_out"]  # best → worst

_LD = re.compile(r"<script[^>]*type\s*=\s*[\"']?application/ld\+json[\"']?[^>]*>(.*?)</script\s*>", re.I | re.S)
_HREF = re.compile(r"""href\s*=\s*["']([^"'#]+)""", re.I)
_HAS_TIME = re.compile(r"T\d|\d:\d")


def ld_blocks(page: str) -> list[str]:
    """Raw text of every JSON-LD script block in an HTML page."""
    return [m.group(1).strip() for m in _LD.finditer(page)]


def load_block(raw: str) -> Any:
    """json.loads, tolerating the usual CMS damage: CDATA wrappers, HTML comments, raw control chars."""
    s = re.sub(r"^\s*(//\s*)?<!\[CDATA\[|(//\s*)?\]\]>\s*$", "", raw.strip())
    s = re.sub(r"^\s*<!--|-->\s*$", "", s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return json.loads(re.sub(r"[\x00-\x1f]", " ", s))  # literal newlines/tabs inside strings


def _types(node: dict[str, Any]) -> set[str]:
    t = node.get("@type")
    raw = t if isinstance(t, list) else [t]
    return {str(x).rsplit("/", 1)[-1].removeprefix("schema:") for x in raw if x}


def is_event(node: Any) -> bool:
    return isinstance(node, dict) and bool(_types(node) & EVENT_TYPES)


def find_events(data: Any) -> Iterator[dict[str, Any]]:
    """Every Event-typed node, depth-first, in document order. Events nested as ``subEvent`` are yielded
    after their parent; other nested objects of an event (offers, location…) are not searched."""
    if isinstance(data, list):
        for x in data:
            yield from find_events(x)
        return
    if not isinstance(data, dict):
        return
    if is_event(data):
        yield data
        yield from find_events(data.get("subEvent") or data.get("subEvents") or [])
        return
    for k, v in data.items():  # @graph, itemListElement[].item, mainEntity, WebPage.about, …
        if isinstance(v, dict | list) and k not in _NOT_EVENTS:
            yield from find_events(v)


_NOT_EVENTS = {"publisher", "author", "breadcrumb", "image", "logo", "potentialAction", "address", "geo"}


def _first(v: Any) -> Any:
    return v[0] if isinstance(v, list) and v else (None if isinstance(v, list) else v)


def _name(v: Any) -> str | None:
    v = _first(v)
    if isinstance(v, dict):
        return clean_text(v.get("name"), 200)
    return clean_text(v, 200) if isinstance(v, str) else None


def _url(v: Any, base: str) -> str | None:
    v = _first(v)
    if isinstance(v, dict):
        v = v.get("url") or v.get("@id")
    if not isinstance(v, str) or not v.strip():
        return None
    u = urljoin(base, htmllib.unescape(v.strip()))
    parts = urlsplit(u)
    return u if parts.scheme in ("http", "https") and parts.netloc else None


def _float(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # NaN


def _location(ev: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    locs = ev.get("location")
    loc_list = locs if isinstance(locs, list) else [locs]
    place = next((x for x in loc_list if isinstance(x, dict) and "VirtualLocation" not in _types(x)), None)
    name: str | None = None
    address: str | None = None
    lat = lon = None
    if place:
        name = clean_text(place.get("name"), 200)
        addr = place.get("address")
        addr = _first(addr)
        if isinstance(addr, dict):
            region = " ".join(
                x for x in (clean_text(addr.get("addressRegion")), clean_text(addr.get("postalCode"))) if x
            )
            address = join_address(
                clean_text(addr.get("streetAddress")), clean_text(addr.get("addressLocality")), region or None
            )
        elif isinstance(addr, str):
            address = clean_text(addr, 300)
        geo = place.get("geo")
        if isinstance(geo, dict):
            lat, lon = _float(geo.get("latitude")), _float(geo.get("longitude"))
    elif isinstance(_first(locs), str):
        address = clean_text(_first(locs), 300)
        name = address.split(",")[0] if address else None
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        lat = lon = None
    if not name and not address:
        name, address = fallback.get("name"), fallback.get("address")
        lat, lon = _float(fallback.get("lat")), _float(fallback.get("lon"))
    return {
        "venue_name": name,
        "address": address or name,
        "lat": lat,
        "lon": lon,
        "geocode_method": "reported" if lat is not None else None,
    }


def _unescape_html(v: Any) -> str | None:
    """Some feeds entity-encode the HTML itself ('&lt;p&gt;…') and backslash-escape quotes: undo both once."""
    if not isinstance(v, str) or not v.strip():
        return None
    s: str = htmllib.unescape(v) if "&lt;" in v and "<" not in v else v
    return s.replace("\\'", "'").replace('\\"', '"')


_SOLD_OUT = re.compile(r"\bsold[\s-]*out\b", re.I)
_PLAIN_AMOUNT = re.compile(r"\s*(US)?\$?\s*\d[\d,]*(\.\d+)?\s*(USD)?\s*", re.I)
_CANCELLED_TITLE = re.compile(r"(?:^|[\s(\[*–—|-])(cancell?ed|postponed)\b", re.I)


def _local_midnight(dt: datetime, tz: str) -> datetime:
    """The calendar date of ``dt`` in the city's zone, as local midnight (for ``date_only`` sources)."""
    zone = ZoneInfo(tz)
    return datetime.combine(dt.astimezone(zone).date(), time(0, 0), zone)


def _strip_site_suffix(title: str, *names: Any) -> str:
    """'LAURA VEIRS with Karl Blau — The Cedar Cultural Center' → 'LAURA VEIRS with Karl Blau' (Squarespace
    appends the site title to the event name). Only an exact venue/organizer name is stripped."""
    for name in names:
        if not isinstance(name, str) or not name.strip():
            continue
        m = re.search(rf"\s+[—–|-]\s+{re.escape(name.strip())}\s*$", title, re.I)
        if m and m.start() >= 2:
            return title[: m.start()].strip()
    return title


def _amounts(v: Any) -> list[float]:
    """'25.00' → [25.0]; '$25 Advance // $30 Day of' → [25.0, 30.0]; 'Free' / None → [].
    Free text without a '$' never yields a price ('… Age 16+' is an age, not $16)."""
    if isinstance(v, str) and not _PLAIN_AMOUNT.fullmatch(v):
        return prices_in_text(v)
    m = money(v)
    return [m] if m is not None else []


def _dt(value: Any, tz: str, ignore_offset: bool) -> datetime | None:
    """Respect offsets — unless the source is known to stamp local wall time with a bogus one
    (``ignore_offset: true``, e.g. '19:00:00+00:00' for a 7 PM show), then re-zone to the city."""
    dt = parse_dt(value, tz)
    if dt is not None and ignore_offset and isinstance(value, str) and _HAS_TIME.search(value):
        naive = parse_dt(re.sub(r"(Z|[+-]\d{2}:?\d{2})$", "", value.strip()), tz)
        return naive or dt
    return dt


def _avail(v: Any) -> str | None:
    if not isinstance(v, str) or not v:
        return None
    return AVAILABILITY.get(v.rsplit("/", 1)[-1].lower())


def _offers(
    ev: dict[str, Any], ctx: ParseContext, base: str, ev_url: str | None, start: datetime
) -> tuple[list[dict[str, Any]], list[float], list[str], list[datetime]]:
    """→ (offer dicts, USD prices seen (incl. 0), offer availabilities, validFrom datetimes)."""
    raw = ev.get("offers")
    items = raw if isinstance(raw, list) else [raw]
    flat: list[dict[str, Any]] = []
    for o in items:
        if not isinstance(o, dict):
            continue
        flat.append(o)
        inner = o.get("offers")  # AggregateOffer may nest the individual offers
        flat.extend(x for x in (inner if isinstance(inner, list) else [inner]) if isinstance(x, dict))
    by_url: dict[str, dict[str, Any]] = {}  # one offer per ticket URL; tiers on the same page are merged
    prices: list[float] = []
    avails: list[str] = []
    valid_from: list[datetime] = []
    trust_vf = bool(ctx.params.get("trust_valid_from", True))
    for o in flat:
        spec = _first(o.get("priceSpecification"))
        spec = spec if isinstance(spec, dict) else {}
        cur = str(o.get("priceCurrency") or spec.get("priceCurrency") or "USD")
        usd = cur.strip().upper() in ("USD", "US$", "$", "")
        vals = [x for k in ("price", "lowPrice", "highPrice") for x in _amounts(o.get(k))]
        nums = [*vals, *_amounts(spec.get("price"))] if usd else []  # non-USD prices are never shown
        prices.extend(nums)
        a = _avail(o.get("availability"))
        if a:
            avails.append(a)
        vf = parse_dt(o.get("validFrom") or o.get("availabilityStarts"), ctx.city.timezone) if trust_vf else None
        # an on-sale time at (or after) the show itself is a placeholder copied from startDate (Mesa Arts Center)
        if vf and vf >= start - timedelta(hours=1):
            vf = None
        if vf:
            valid_from.append(vf)
        url = _url(o.get("url"), base) or ev_url
        if not url:
            continue
        status = a or "unknown"
        if vf and vf > ctx.fetched_at and status in ("unknown", "on_sale"):
            status = "not_yet_on_sale"
        pos = [n for n in nums if n > 0]
        cur_offer = by_url.get(url)
        if cur_offer is None:
            host = urlsplit(url).netloc.lower().removeprefix("www.")
            by_url[url] = {
                "seller": _name(o.get("seller")) or _name(o.get("offeredBy")) or _seller(host, ctx.source.name),
                "kind": "primary",
                "url": url,
                "price_min": min(pos) if pos else None,
                "price_max": max(pos) if pos else None,
                "availability": status,
                "source_id": ctx.source.id,
                "fetched_at": ctx.fetched_at,
            }
            continue
        if pos:
            lo, hi = cur_offer["price_min"], cur_offer["price_max"]
            cur_offer["price_min"] = min(pos) if lo is None else min(lo, *pos)
            cur_offer["price_max"] = max(pos) if hi is None else max(hi, *pos)
        if status != "unknown" and (
            cur_offer["availability"] == "unknown" or _rank(status) < _rank(cur_offer["availability"])
        ):
            cur_offer["availability"] = status
    return list(by_url.values())[:4], prices, avails, valid_from


def _rank(availability: str) -> int:
    return _AVAIL_RANK.index(availability) if availability in _AVAIL_RANK else len(_AVAIL_RANK)


_SELLERS = {
    "ticketmaster.com": "Ticketmaster",
    "livenation.com": "Live Nation",
    "axs.com": "AXS",
    "etix.com": "Etix",
    "dice.fm": "DICE",
    "seetickets.us": "See Tickets",
    "tixr.com": "Tixr",
    "eventbrite.com": "Eventbrite",
    "ticketweb.com": "TicketWeb",
    "prekindle.com": "Prekindle",
    "showclix.com": "ShowClix",
    "frontgatetickets.com": "Front Gate Tickets",
    "ticketfly.com": "Ticketfly",
    "universe.com": "Universe",
    "eventim.us": "Eventim",
    "holdmyticket.com": "HoldMyTicket",
    "tixfox.com": "TixFox",
    "opendate.io": "Opendate",
}


def _seller(host: str, fallback: str) -> str:
    for h, name in _SELLERS.items():
        if host == h or host.endswith("." + h):
            return name
    return fallback


def _status(ev: dict[str, Any]) -> str | None:
    s = str(ev.get("eventStatus") or "").rsplit("/", 1)[-1].lower()
    if "cancel" in s:
        return "cancelled"
    if "postpon" in s:
        return "postponed"
    if "reschedul" in s:
        return "rescheduled"
    if "movedonline" in s:
        return "moved_online"
    return None


def _names(v: Any, limit: int = 12) -> list[str]:
    items = v if isinstance(v, list) else [v]
    out = [n for n in (_name(x) for x in items) if n and n not in _TYPE_WORDS]
    return list(dict.fromkeys(out))[:limit]


# placeholder values some CMSes emit instead of a performer's name ("performer": "Organization")
_TYPE_WORDS = {"Organization", "Person", "PerformingGroup", "MusicGroup", "TheaterGroup", "DanceGroup", "Thing"}


def _image(v: Any, base: str) -> str | None:
    return _url(v, base)


def _category(ctx: ParseContext, types: set[str], title: str, desc: str | None) -> str:
    """category_map (by @type, then title keyword) → @type default refined by the title → title classifier.
    Venue blurbs mention everything ("volunteer", "singles", "family"), so descriptions are only used
    when ``classify_description: true``."""
    cmap: dict[str, str] = ctx.params.get("category_map", {})
    desc_ok = bool(ctx.params.get("classify_description", False))
    for t in sorted(types):
        if t in cmap:
            return cmap[t]
    low = title.lower()
    for key, cat in cmap.items():
        if key.lower() in low:
            return cat
    typed = next((TYPE_CATEGORY[t] for t in sorted(types) if t in TYPE_CATEGORY), None)
    if typed:
        # the title can still say something more specific ("Open Mic Night", "Comedy Showcase", "Trivia")
        hit = ctx.tax.classify(title, default=typed)
        return hit.category if hit.matched else typed
    if "Festival" in types:
        hit = ctx.tax.classify(title, desc if desc_ok else None, default="music.festival")
        return hit.category
    default = ctx.params.get("default_category", "other.uncategorized")
    return ctx.tax.classify(title, desc if desc_ok else None, default=default).category


@register
class JsonLdAdapter(Adapter):
    name = "jsonld"

    def required_params(self) -> tuple[str, ...]:
        return ("urls",)

    def check_config(self, source: Any) -> None:
        if "urls" not in source.params and "url" not in source.params:
            from gotc.adapters.base import AdapterConfigError

            raise AdapterConfigError(f"{source.id}: missing params ['urls']")

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        raw_urls = p.get("urls") or p.get("url")
        urls: list[str] = [str(u) for u in (raw_urls if isinstance(raw_urls, list) else [raw_urls])]
        follow = re.compile(p["follow"]) if p.get("follow") else None
        max_follow = min(int(p.get("max_follow", 30)), 80)  # hard cap: never more than 80 detail pages a run
        interval = max(float(ctx.source.min_interval_s or 0), 2.0)
        listing: list[Payload] = []
        links: list[str] = []
        for u in urls:
            host = urlsplit(u).netloc
            ctx.http.host_intervals[host] = max(ctx.http.host_intervals.get(host, 0.0), interval)
            r = ctx.http.get(u, respect_robots=self.respect_robots)
            listing.append(Payload.from_response(r, ctx.now, "html", role="listing"))
            if follow:
                for href in _HREF.findall(r.text):
                    full = urljoin(r.url, htmllib.unescape(href.strip()))
                    if follow.search(full) and full not in links and full not in urls:
                        links.append(full)
        if not follow and not any(ld_blocks(pl.text) for pl in listing):
            raise ValueError("no JSON-LD blocks on the listing page(s) — layout changed or markup removed?")
        if follow and not links and not any(ld_blocks(pl.text) for pl in listing):
            raise ValueError("no detail links matched `follow` and no JSON-LD on the listing page(s)")
        details: list[Payload] = []
        failed: list[str] = []
        for link in links[:max_follow]:
            host = urlsplit(link).netloc
            ctx.http.host_intervals[host] = max(ctx.http.host_intervals.get(host, 0.0), interval)
            try:
                r = ctx.http.get(link, respect_robots=self.respect_robots)
            except FetchError as e:
                if e.kind == "robots_disallowed":
                    raise
                failed.append(f"{link}: {e}")
                continue
            details.append(Payload.from_response(r, ctx.now, "html", role="detail"))
        if links and len(failed) > max(2, len(links[:max_follow]) // 2):
            raise ValueError(f"{len(failed)} of {len(links[:max_follow])} detail pages failed, e.g. {failed[0]}")
        complete = len(links) <= max_follow and not failed
        return FetchResult([*details, *listing], complete=complete)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        p = ctx.params
        base = payload.url
        tz = ctx.city.timezone
        horizon = ctx.fetched_at + timedelta(days=int(p.get("horizon_days", 180)))
        fallback = p.get("venue") or {}
        for raw in ld_blocks(payload.text):
            try:
                data = load_block(raw)
            except json.JSONDecodeError as e:
                if '"Event' in raw or "Event" in raw[:400]:
                    yield {"_reject": f"unparseable JSON-LD block with events: {e}", "_hint": base}
                continue
            for ev in find_events(data):
                yield from self._record(ev, ctx, base, tz, horizon, fallback)

    def _record(
        self,
        ev: dict[str, Any],
        ctx: ParseContext,
        base: str,
        tz: str,
        horizon: datetime,
        fallback: dict[str, Any],
    ) -> Iterator[dict[str, Any]]:
        p = ctx.params
        types = _types(ev)
        title = clean_text(str(ev.get("name") or "").replace("\\'", "'").replace('\\"', '"'), 300)
        raw_start = _first(ev.get("startDate"))
        start = _dt(raw_start, tz, bool(p.get("ignore_offset")))
        if not title or len(title) < 2 or start is None:
            yield {"_reject": "event without name/startDate", "_hint": f"{base} {str(ev.get('name'))[:80]}"}
            return
        end = _dt(_first(ev.get("endDate")), tz, bool(p.get("ignore_offset")))
        all_day = not _HAS_TIME.search(str(raw_start))
        if p.get("date_only"):  # the source's clock times are known to be wrong: keep the (correct) date only
            start, all_day = _local_midnight(start, tz), True
            end = _local_midnight(end, tz) if end is not None else None
        if end is not None and end < start:
            end = None
        last = end or (start + timedelta(days=1) if all_day else start)  # an all-day event lasts its whole day
        if last < ctx.fetched_at - timedelta(hours=6) or start > horizon:
            return  # windowed out (past or beyond the horizon), like the ICS adapter
        ev_url = _url(ev.get("url"), base) or (_url(ev.get("@id"), base) if "#" not in str(ev.get("@id")) else None)
        ev_url = ev_url or base
        desc_html = _unescape_html(ev.get("description"))
        desc = clean_text(desc_html, 4000)
        offers, prices, avails, valid_from = _offers(ev, ctx, base, ev_url, start)
        positive = [x for x in prices if x > 0]
        free_flag = ev.get("isAccessibleForFree") in (True, "true", "True", "TRUE")
        zero_free = bool(p.get("zero_is_free")) and prices and not positive
        price: dict[str, Any] = {}
        availability = "unknown"
        if positive:
            price = {"min": min(positive), "max": max(positive), "note": p.get("price_note")}
        elif free_flag or zero_free or says_free(title, desc):
            price = {"is_free": True}
            availability = "free_no_ticket"
        if avails:
            availability = min(avails, key=_AVAIL_RANK.index)  # best availability across ticket tiers
        elif offers and any(o["availability"] == "not_yet_on_sale" for o in offers):
            availability = "not_yet_on_sale"
        future_sale = sorted(v for v in valid_from if v > ctx.fetched_at)
        if future_sale and availability in ("unknown", "on_sale"):
            availability = "not_yet_on_sale"
        status = _status(ev)
        if status in ("cancelled", "postponed"):
            availability = status
        elif m := _CANCELLED_TITLE.search(title):  # "An Evening with Eric Idle – CANCELED"
            availability = "postponed" if m.group(1).lower().startswith("post") else "cancelled"
        elif availability == "unknown" and _SOLD_OUT.search(title):
            availability = "sold_out"  # "Oliver Malcolm - SOLD OUT": the venue says so in the title
        loc = _location(ev, fallback)
        title = _strip_site_suffix(title, loc.get("venue_name"), p.get("organizer"), fallback.get("name"))
        record_key = _url(ev.get("@id"), base) or ev_url or title
        performers = _names(ev.get("performer") or ev.get("performers"))
        extras: dict[str, Any] = {
            "schema_type": ",".join(sorted(types)),
            "performers": "; ".join(performers)[:300] or None,
            "image": _image(ev.get("image"), base),
            "onsale_at": min(valid_from).isoformat() if valid_from else None,
            "event_status": status,
            "doors": clean_text(ev.get("doorTime"), 40),
            "age_restriction": clean_text(ev.get("typicalAgeRange"), 40),
        }
        organizer = _name(ev.get("organizer")) or p.get("organizer")
        rec = ctx.base(
            f"{stable_id(record_key)}:{start.isoformat()}",
            title=title,
            description=desc,
            url=ev_url,
            category=_category(ctx, types, title, desc),
            source_categories=sorted(types),
            tags=list(p.get("tags", [])),
            start=start,
            end=end,
            all_day=all_day,
            location=loc,
            organizer=organizer,
            price=price,
            offers=offers,
            availability=availability,
            extras={k: v for k, v in extras.items() if v is not None},
            _html=desc_html,
        )
        if future_sale:
            rec["registration"] = {
                "opens_at": future_sale[0],
                "url": next((o["url"] for o in offers), ev_url),
                "evidence": f"schema.org offers.validFrom = {future_sale[0].isoformat()} (tickets go on sale)",
                "method": "reported",
            }
        yield rec
