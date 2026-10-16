"""Communico library calendars (Miami-Dade Public Library System and other Communico/"Attend" libraries).

Endpoint: ``{base}/eeventcaldata?event_type=0&req={"private":false,"date":"YYYY-MM-DD","days":1,...}``
This is the JSON the library's own calendar page loads. It is **undocumented**, so medium-risk: robots.txt
allows it (mdpls.org disallows only search/results pages), each day is ~0.5 MB so we request one day at a
time for a short horizon, at PoliteClient's per-host pace, once a day. Drop the source if the library objects.

Fields used: ``id, title, sub_title, description, raw_start_time/raw_end_time`` (local wall-clock),
``location`` (branch), ``venue_room``, ``url``, ``allow_reg/reg_url/max_attendee/total_registrants``,
``registration_cost``, ``tags``, ``ages``, ``event_type`` (INPERSON/VIRTUAL), ``changed`` (cancel/reschedule).
Staff contact names (``event_contact``) are never mapped.

    params:
      base_url: https://www.mdpls.org
      horizon_days: 7
      venue_label: Miami-Dade Public Library
      category_map: {Art Exhibition: arts.museum}   # tag/age labels, checked in config order
      default_category: arts.books
      skip_all_day: true    # "All day" rows are exhibits/displays/passive programs, not events
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text, money, parse_dt, says_free


@register
class CommunicoAdapter(Adapter):
    name = "communico"

    def required_params(self) -> tuple[str, ...]:
        return ("base_url",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        url = p["base_url"].rstrip("/") + "/eeventcaldata"
        local = ctx.now.astimezone(ZoneInfo(ctx.city.timezone)).date()
        payloads: list[Payload] = []
        for offset in range(int(p.get("horizon_days", 7))):
            day = local + timedelta(days=offset)
            req = {"private": False, "date": day.isoformat(), "days": 1, "locations": [], "ages": [], "types": []}
            r = ctx.http.get(url, params={"event_type": 0, "req": json.dumps(req, separators=(",", ":"))})
            if not isinstance(r.json(), list):
                raise ValueError("Communico eeventcaldata did not return a JSON array — endpoint changed?")
            payloads.append(Payload.from_response(r, ctx.now, "json", date=day.isoformat()))
        return FetchResult(payloads, complete=True)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        p = ctx.params
        tz = ctx.city.timezone
        cmap: dict[str, str] = p.get("category_map", {})
        data = json.loads(payload.content)
        if not isinstance(data, list):
            yield {"_reject": "payload is not a JSON array", "_hint": payload.text[:200]}
            return
        for ev in data:
            if not isinstance(ev, dict):
                yield {"_reject": "event is not an object", "_hint": str(ev)[:200]}
                continue
            title = clean_text(ev.get("title"), 300)
            start = parse_dt(ev.get("raw_start_time") or ev.get("event_start"), tz)
            if not ev.get("id") or not title or start is None:
                yield {"_reject": "missing id/title/start", "_hint": json.dumps(ev)[:200]}
                continue
            if str(ev.get("private_event")) == "1":
                continue
            tags = [t for t in (ev.get("tagsArray") or _split(ev.get("tags"))) if t]
            online_only = "Online" in tags and "In-Person" not in tags
            virtual = str(ev.get("event_type", "")).upper() == "VIRTUAL" or online_only
            if virtual and not p.get("include_virtual", False):
                continue  # online-only: not something to get off the couch for
            all_day = str(ev.get("time_string", "")).strip().lower() == "all day"
            if all_day and p.get("skip_all_day", True):
                continue
            end = parse_dt(ev.get("raw_end_time") or ev.get("event_end"), tz)
            sub = clean_text(ev.get("sub_title"), 200)
            html = "\n".join(str(x) for x in (ev.get("description"), ev.get("long_description")) if x)
            desc = clean_text(html, 4000)
            if sub:
                desc = f"{sub}\n\n{desc}" if desc else sub
            ages = [a for a in (ev.get("agesArray") or _split(ev.get("ages"))) if a]
            cats = [*tags, *ages]
            category = (
                next((cmap[k] for k in cmap if k in cats), None)
                or ctx.tax.classify(
                    title, " ".join(cats), desc, default=p.get("default_category", "arts.books")
                ).category
            )
            reg = str(ev.get("allow_reg")) == "1" or str(ev.get("third_party_reg")) == "1"
            cap = _int(ev.get("max_attendee"))
            registered = _int(ev.get("total_registrants"))
            changed = str(ev.get("changed") or "").lower()
            if "cancel" in changed or "cancel" in str(ev.get("changed_reason") or "").lower():
                availability = "cancelled"
            elif reg and cap and registered is not None and registered >= cap:
                availability = "waitlist" if str(ev.get("allow_waitlist")) == "1" else "registration_closed"
            elif reg:
                availability = "registration_open"
            else:
                availability = "unknown"
            cost = money(ev.get("registration_cost"))
            if cost:
                price: dict[str, Any] = {"min": cost, "max": cost}
            elif says_free(title, desc):
                price = {"is_free": True}
            else:
                price = {}
            branch = clean_text(ev.get("location") or ev.get("library"), 160)
            label = p.get("venue_label")
            venue = f"{label} – {branch}" if label and branch else branch
            room = clean_text(ev.get("venue_room") or ev.get("venue_name"), 120)
            reg_url = ev.get("reg_url")
            extras: dict[str, Any] = {}
            if cap:
                extras["capacity"] = cap
            if reg and registered is not None:
                extras["registered"] = registered
            yield ctx.base(
                str(ev["id"]),
                title=title,
                description=desc,
                url=ev.get("url") if str(ev.get("url", "")).startswith("http") else None,
                kind="recurring" if str(ev.get("recurring_id") or "0") not in ("", "0") else "one_off",
                category=category,
                source_categories=cats,
                tags=[*p.get("tags", []), *(["registration_required"] if reg else [])],
                start=start,
                end=end if end and end >= start else None,
                all_day=all_day,
                location={"venue_name": f"{venue} ({room})" if venue and room else venue},
                organizer=label or ctx.source.name,
                price=price,
                availability=availability,
                offers=[
                    {
                        "seller": label or ctx.source.name,
                        "kind": "registration",
                        "url": reg_url,
                        "availability": availability if availability != "unknown" else "registration_open",
                        "source_id": ctx.source.id,
                        "fetched_at": ctx.fetched_at,
                    }
                ]
                if reg and isinstance(reg_url, str) and reg_url.startswith("http")
                else [],
                extras=extras,
                _html=html,
            )


def _split(v: Any) -> list[str]:
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


def _int(v: Any) -> int | None:
    try:
        n = int(str(v))
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None
