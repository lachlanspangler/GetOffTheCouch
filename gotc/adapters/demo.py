"""DEMO adapter: turns config/demo/events.yaml into SourceEvents relative to the fetch time.

Only used by `gotc demo`, which runs the real pipeline into a separate data dir and exports to
web/public/demo/. Every record has ``is_demo=True``; the real exporter drops demo records.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.settings import CONFIG_DIR


@register
class DemoAdapter(Adapter):
    name = "demo"
    respect_robots = False

    def fetch(self, ctx: FetchContext) -> FetchResult:
        content = (CONFIG_DIR / "demo" / "events.yaml").read_bytes()
        return FetchResult([Payload("file://config/demo/events.yaml", 200, content, ctx.now, "yaml")])

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        data = yaml.safe_load(payload.content)
        src = ctx.params["src"]
        tz = ZoneInfo(ctx.city.timezone)
        anchor = datetime.fromisoformat(ctx.params["anchor"]) if ctx.params.get("anchor") else ctx.fetched_at
        # how far *this* fetch is before the anchor, in [0, 1]: drives the fake listing/price drift
        lag = max(0.0, min(1.0, (anchor - ctx.fetched_at).total_seconds() / (72 * 3600)))
        base_day = anchor.astimezone(tz).date()
        for e in data["events"]:
            if e["src"] != src:
                continue
            hh, mm = (int(x) for x in str(e.get("at", "12:00")).split(":"))
            for k in range(int(e.get("weekly", 1))):
                start = datetime.combine(base_day + timedelta(days=int(e["day"]) + 7 * k), time(hh, mm), tz)
                offers = []
                for o in e.get("offers", []):
                    lo = o.get("min")
                    listings = o.get("listings")
                    if listings is not None:
                        listings = int(listings * (1 - o.get("drop", 0) * (1 - lag)))
                    if lo is not None and o.get("rise"):
                        lo = round(lo * (1 + o["rise"] * (1 - lag)), 2)
                    offers.append(
                        {
                            "seller": o["seller"],
                            "kind": o["kind"],
                            "url": f"https://example.org/demo/{e['id']}/{o['kind']}",
                            "price_min": lo,
                            "price_max": o.get("max"),
                            "listing_count": listings,
                            "availability": "on_sale",
                            "source_id": ctx.source.id,
                            "fetched_at": ctx.fetched_at,
                        }
                    )
                reg = None
                if e.get("closes_in_days") is not None:
                    closes = datetime.combine(base_day + timedelta(days=int(e["closes_in_days"])), time(23, 59), tz)
                    reg = {
                        "closes_at": closes,
                        "early_bird_ends_at": datetime.combine(
                            base_day + timedelta(days=int(e["early_bird_days"])), time(23, 59), tz
                        )
                        if e.get("early_bird_days") is not None
                        else None,
                        "signup_types": e.get("signup", []),
                        "skill_levels": e.get("skill", []),
                        "url": e.get("reg_url") or e.get("url"),
                        "method": "reported",
                        "confidence": 1.0,
                    }
                yield ctx.base(
                    f"{e['id']}:{k}",
                    title=e["title"],
                    description=e.get("desc"),
                    url=e.get("url") or f"https://example.org/demo/{e['id']}",
                    kind=e.get("kind", "recurring" if e.get("weekly") else "one_off"),
                    category=e["category"],
                    start=start,
                    end=start + timedelta(hours=3) if not e.get("all_day") else None,
                    all_day=bool(e.get("all_day")),
                    location={
                        "venue_name": e.get("venue"),
                        "lat": e.get("lat"),
                        "lon": e.get("lon"),
                        "geocode_method": "reported",
                    },
                    price={"is_free": True} if e.get("free") else dict(e.get("price") or {}),
                    offers=offers,
                    registration=reg,
                    availability="free_no_ticket" if e.get("free") else "on_sale",
                    venue_capacity=e.get("capacity"),
                    is_demo=True,
                )
