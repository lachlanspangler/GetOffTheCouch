"""RSS 2.0 feeds with the RSS "event" module (``xmlns:ev="http://purl.org/rss/1.0/modules/event/"``).

Venue sites built on the carbonhouse CMS publish ``/events/rss`` (ACL Live in Austin, Denver Arts & Venues'
Performing Arts Complex and Coliseum, the Ryman in Nashville, many arenas and theatres); other CMSes emit the
same module. Each ``<item>`` is one show (or one run of a show) with ``ev:startdate``/``ev:enddate`` (UTC,
``Z``), ``ev:location`` (the room) and sometimes ``ev:type``/``ev:organizer``. The feed is published for
syndication, keyless; robots.txt is honored by ``PoliteClient``.

    params:
      url: https://www.acllive.com/events/rss          # or a list of feeds
      horizon_days: 180
      venue: {name: ACL Live, address: "310 W Willie Nelson Blvd, Austin, TX 78701"}   # default location
      venues: {"Dazzle": "1512 Curtis St, Denver, CO 80202"}    # ev:location → street address (optional)
      default_category: music.concert
      category_map: {Broadway: arts.theater}   # ev:type, ev:location or a title keyword → taxonomy id
      classify_description: false              # venue blurbs mislead the keyword classifier
      organizer: ACL Live

Prices are never read from descriptions here: venue blurbs mention parking, merch and drink prices. Ticket
links inside the description become offers in ``normalize`` (as for every adapter).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register, stable_id
from gotc.adapters.bibliocommons import safe_xml
from gotc.adapters.common import clean_text, parse_dt, says_free

EV = "{http://purl.org/rss/1.0/modules/event/}"


def _text(item: ET.Element, tag: str) -> str | None:
    v = item.findtext(tag)
    return v.strip() if v and v.strip() else None


@register
class RssEventsAdapter(Adapter):
    name = "rss_events"

    def required_params(self) -> tuple[str, ...]:
        return ("url",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        urls = ctx.params["url"] if isinstance(ctx.params["url"], list) else [ctx.params["url"]]
        payloads = []
        for u in urls:
            r = ctx.http.get(u, respect_robots=self.respect_robots)
            root = safe_xml(r.content)
            channel = root.find("channel")
            if root.tag != "rss" or channel is None:
                raise ValueError(f"{u} did not return an RSS document (feed moved or disabled?)")
            items = channel.findall("item")
            if items and not any(i.find(f"{EV}startdate") is not None for i in items):
                raise ValueError(f"{u}: RSS items carry no ev:startdate (not an event feed, or the module was dropped)")
            payloads.append(Payload.from_response(r, ctx.now, "xml"))
        return FetchResult(payloads, complete=True)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        p = ctx.params
        tz = ctx.city.timezone
        zone = ZoneInfo(tz)
        root = safe_xml(payload.content)
        horizon = ctx.fetched_at + timedelta(days=int(p.get("horizon_days", 180)))
        fallback: dict[str, Any] = p.get("venue") or {}
        addresses: dict[str, str] = p.get("venues") or {}
        for item in root.iter("item"):
            title = clean_text(item.findtext("title"), 300)
            raw_start = _text(item, f"{EV}startdate")
            start = parse_dt(raw_start, tz)
            link = _text(item, "link")
            guid = _text(item, "guid") or link or title
            if not title or start is None:
                yield {"_reject": "item without title/ev:startdate", "_hint": f"{guid} {title}"}
                continue
            start = start.astimezone(zone)  # feeds stamp UTC ('Z'); store the city's wall clock
            end = parse_dt(_text(item, f"{EV}enddate"), tz)
            end = end.astimezone(zone) if end is not None else None
            if end is not None and end <= start:
                end = None  # carbonhouse repeats the start as the end when there is no end time
            all_day = "T" not in str(raw_start) and ":" not in str(raw_start)
            last = end or (start + timedelta(days=1) if all_day else start)
            if last < ctx.fetched_at - timedelta(hours=6) or start > horizon:
                continue  # windowed out, like the ICS and JSON-LD adapters
            html = item.findtext("description")
            desc = clean_text(html, 4000)
            room = clean_text(_text(item, f"{EV}location"), 200)
            kind = clean_text(_text(item, f"{EV}type"), 80)
            venue_name = room or fallback.get("name")
            address = addresses.get(room or "") or fallback.get("address")
            yield ctx.base(
                f"{stable_id(guid)}:{start.isoformat()}",
                title=title,
                description=desc,
                url=link if link and link.startswith("http") else None,
                category=self._category(ctx, title, kind, room, desc),
                source_categories=[x for x in (kind, room) if x],
                tags=list(p.get("tags", [])),
                start=start,
                end=end,
                all_day=all_day,
                location={"venue_name": venue_name, "address": address or venue_name},
                organizer=clean_text(_text(item, f"{EV}organizer")) or p.get("organizer"),
                price={"is_free": True} if says_free(title) else {},
                availability="free_no_ticket" if says_free(title) else "unknown",
                _html=html,
            )

    @staticmethod
    def _category(ctx: ParseContext, title: str, kind: str | None, room: str | None, desc: str | None) -> str:
        cmap: dict[str, str] = ctx.params.get("category_map", {})
        for key in (kind, room):
            if key and key in cmap:
                return cmap[key]
        low = title.lower()
        for key, cat in cmap.items():
            if key.lower() in low:
                return cat
        use_desc = bool(ctx.params.get("classify_description", False))
        return ctx.tax.classify(
            title, kind, desc if use_desc else None, default=ctx.params.get("default_category", "other.uncategorized")
        ).category
