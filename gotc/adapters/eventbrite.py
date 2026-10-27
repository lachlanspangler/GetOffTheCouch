"""Eventbrite Platform API v3, organizer-scoped (the public event search endpoint was retired in 2020).

Needs EVENTBRITE_TOKEN (a free private token: https://www.eventbrite.com/platform/api-keys), sent as a Bearer
header so it never appears in a stored URL. Without it the unit shows "disabled: needs EVENTBRITE_TOKEN".

Which organizers to follow is per city config (``params.organizers: {<city>: [<organizer id>, …]}``). An organizer
id is the number at the end of an eventbrite.com/o/… page URL; only add organizers whose events are public and
in the city. A city with no organizers listed fetches nothing and stays healthy (0 records is expected).

  GET https://www.eventbriteapi.com/v3/organizers/{id}/events/?status=live&order_by=start_asc
      &expand=venue,ticket_availability&page_size=50[&continuation=…]
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text, dig, parse_dt


@register
class EventbriteAdapter(Adapter):
    name = "eventbrite"
    respect_robots = False  # documented API (robots.txt governs crawlers of the website, not the API)
    BASE = "https://www.eventbriteapi.com/v3/organizers/{id}/events/"

    def fetch(self, ctx: FetchContext) -> FetchResult:
        token = ctx.secret("EVENTBRITE_TOKEN")
        organizers = [str(o) for o in (ctx.params.get("organizers") or {}).get(ctx.city.slug, [])]
        headers = {"Authorization": f"Bearer {token}"}
        payloads: list[Payload] = []
        complete = True
        for org in organizers:
            cont: str | None = None
            for page in range(1, int(ctx.params.get("max_pages", 5)) + 1):
                q: dict[str, str | int | float] = {
                    "status": "live",
                    "order_by": "start_asc",
                    "expand": "venue,ticket_availability",
                    "page_size": 50,
                }
                if cont:
                    q["continuation"] = cont
                r = ctx.http.get(self.BASE.format(id=org), params=q, headers=headers, respect_robots=False)
                payloads.append(Payload.from_response(r, ctx.now, "json", page=page))
                pag = r.json().get("pagination") or {}
                if not pag.get("has_more_items"):
                    break
                cont = pag.get("continuation")
            else:
                complete = False
        return FetchResult(payloads, complete=complete)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        for ev in json.loads(payload.content).get("events", []):
            title = clean_text(dig(ev, "name.text"), 300)
            tz = dig(ev, "start.timezone") or ctx.city.timezone
            start = parse_dt(dig(ev, "start.local"), tz)
            if not title or start is None:
                yield {"_reject": "missing name/start", "_hint": str(ev.get("id"))}
                continue
            if ev.get("online_event"):
                yield {"_reject": "online-only event", "_hint": str(ev.get("id"))}
                continue
            venue = ev.get("venue") or {}
            addr = venue.get("address") or {}
            ta = ev.get("ticket_availability") or {}
            lo = dig(ta, "minimum_ticket_price.major_value")
            hi = dig(ta, "maximum_ticket_price.major_value")
            free = bool(ev.get("is_free"))
            avail = (
                "cancelled"
                if ev.get("status") == "canceled"
                else "sold_out"
                if ta.get("is_sold_out")
                else "on_sale"
                if ta.get("has_available_tickets")
                else "unknown"
            )
            desc = clean_text(dig(ev, "description.text"), 4000)
            cat = ctx.tax.classify(title, desc, default="other.uncategorized").category
            yield ctx.base(
                str(ev["id"]),
                title=title,
                url=ev.get("url"),
                description=desc,
                category=cat,
                start=start,
                end=parse_dt(dig(ev, "end.local"), tz),
                organizer=dig(ev, "organizer.name"),
                location={
                    "venue_name": venue.get("name"),
                    "address": addr.get("localized_address_display"),
                    "lat": _f(addr.get("latitude")),
                    "lon": _f(addr.get("longitude")),
                    "geocode_method": "reported" if addr.get("latitude") else None,
                },
                price={"is_free": True} if free else ({"min": _f(lo), "max": _f(hi)} if lo is not None else {}),
                offers=[
                    {
                        "seller": "Eventbrite",
                        "kind": "rsvp" if free else "primary",
                        "url": ev["url"],
                        "price_min": None if free else _f(lo),
                        "price_max": None if free else _f(hi),
                        "availability": avail,
                        "source_id": ctx.source.id,
                        "fetched_at": ctx.fetched_at,
                    }
                ]
                if ev.get("url")
                else [],
                availability=avail,
            )


def _f(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
