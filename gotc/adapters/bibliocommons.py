"""BiblioCommons Events RSS — public library calendars (Hennepin County, Chicago, Boston, …).

Feed: ``https://gateway.bibliocommons.com/v2/libraries/<lib>/rss/events?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&page=N``
This is the RSS feed each library links from ``<lib>.bibliocommons.com/v2/events``. Keyless, 25 items per page,
no total count, so we page until a short page (or a page that repeats ids). The ``bc:`` namespace carries
local + UTC times, branch address/geo, cancellation, and registration (required/full/capacity/registered).
The undocumented JSON gateway (``/v2/libraries/<lib>/events``) ignores date filters — don't use it.

    params:
      library: hclib
      horizon_days: 14
      venue_label: Hennepin County Library      # venue_name = "<label> – <branch>"
      category_map: {Kids: family.kids, Book Clubs: arts.books}   # checked in config order
      default_category: arts.books
      cities: [Minneapolis]                     # optional: keep only branches in these cities
      include_virtual: false                    # default: online-only events are skipped

XML safety: parsed with the stdlib ``xml.etree`` parser. Python's expat never resolves external entities
(no XXE) and Python ≥ 3.12 ships expat ≥ 2.6 with billion-laughs protection; on top of that we refuse any
payload that declares a DOCTYPE/ENTITY, which a legitimate RSS feed never needs.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text, join_address, parse_dt, says_free
from gotc.adapters.mapped import sane_coords

BC = "{http://bibliocommons.com/rss/1.0/modules/event/}"
GATEWAY = "https://gateway.bibliocommons.com/v2/libraries/{lib}/rss/events"
PAGE_SIZE = 25
_UNSAFE = re.compile(rb"<!(DOCTYPE|ENTITY)", re.I)


_BARE_AMP = re.compile(rb"&(?!(?:[a-zA-Z][a-zA-Z0-9]{1,31}|#[0-9]{1,7}|#x[0-9a-fA-F]{1,6});)")


def safe_xml(content: bytes) -> ET.Element:
    """Parse untrusted feed XML. Refuses DTDs/entities outright (see module docstring)."""
    if _UNSAFE.search(content):
        raise ValueError("refusing XML with a DOCTYPE/ENTITY declaration")
    try:
        return ET.fromstring(content)
    except ET.ParseError:
        # common real-world breakage: bare "&" in titles ("Hall & Oates"). Escape those and retry once;
        # if it still fails, it's a format change → ValueError (health: format_changed), never a crash.
        fixed = _BARE_AMP.sub(b"&amp;", content)
        try:
            return ET.fromstring(fixed)
        except ET.ParseError as e:
            raise ValueError(f"feed is not well-formed XML: {e}") from e


@register
class BiblioCommonsAdapter(Adapter):
    name = "bibliocommons"

    def required_params(self) -> tuple[str, ...]:
        return ("library",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        local = ctx.now.astimezone(ZoneInfo(ctx.city.timezone)).date()
        q: dict[str, str | int] = {
            "startDate": local.isoformat(),
            "endDate": (local + timedelta(days=int(p.get("horizon_days", 14)))).isoformat(),
        }
        url = GATEWAY.format(lib=p["library"])
        payloads: list[Payload] = []
        seen: set[str] = set()
        complete = True
        for page in range(1, int(p.get("max_pages", 40)) + 1):
            q["page"] = page
            r = ctx.http.get(url, params=q)
            root = safe_xml(r.content)
            if root.tag != "rss" or root.find("channel") is None:
                raise ValueError("BiblioCommons did not return an RSS document — feed moved or disabled?")
            guids = [(i.findtext("guid") or i.findtext("link") or "") for i in root.iter("item")]
            fresh = [g for g in guids if g not in seen]
            if not fresh:
                break  # past the last page (or the server ignored ``page``)
            seen.update(fresh)
            payloads.append(Payload.from_response(r, ctx.now, "xml", page=page))
            if len(guids) < PAGE_SIZE:
                break
        else:
            complete = False
        return FetchResult(payloads, complete=complete)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        p = ctx.params
        tz = ctx.city.timezone
        root = safe_xml(payload.content)
        cities = {c.lower() for c in p.get("cities", [])}
        cmap: dict[str, str] = p.get("category_map", {})
        for item in root.iter("item"):
            link = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or link).strip()
            rid = guid.rstrip("/").rsplit("/", 1)[-1]
            title = clean_text(item.findtext("title"), 300)
            start = parse_dt(item.findtext(f"{BC}start_date_local"), tz) or parse_dt(
                item.findtext(f"{BC}start_date"), tz
            )
            if not rid or not title or start is None:
                yield {"_reject": "missing id/title/start", "_hint": f"{guid} {title}"}
                continue
            all_day = "T" not in (item.findtext(f"{BC}start_date_local") or "T")  # "2026-10-17" = all-day
            if _flag(item, "is_virtual") and not p.get("include_virtual", False):
                continue
            loc = item.find(f"{BC}location")
            branch = _text(loc, "name")
            city = (_text(loc, "city") or "").strip(" ,")
            if cities and city.lower() not in cities:
                continue
            end = parse_dt(item.findtext(f"{BC}end_date_local"), tz) or parse_dt(item.findtext(f"{BC}end_date"), tz)
            html = item.findtext("description")
            desc = clean_text(html, 4000)
            cats = [c for c in (clean_text(x.text) for x in item.findall("category")) if c]
            category = (
                next((cmap[k] for k in cmap if k in cats), None)
                or ctx.tax.classify(
                    title, " ".join(cats), desc, default=p.get("default_category", "arts.books")
                ).category
            )
            lat, lon = sane_coords(_float(_text(loc, "latitude")), _float(_text(loc, "longitude")), ctx)
            street = " ".join(x for x in (_text(loc, "number"), _text(loc, "street")) if x)
            reg = item.find(f"{BC}registration_info")
            required, full = _flag(reg, "is_required"), _flag(reg, "is_full")
            capacity, registered = _int(_text(reg, "capacity")), _int(_text(reg, "number_registered"))
            if _flag(item, "is_cancelled"):
                availability = "cancelled"
            elif required and full:
                availability = "registration_closed"
            elif required:
                availability = "registration_open"
            else:
                availability = "unknown"
            label = p.get("venue_label")
            extras: dict[str, Any] = {}
            if capacity:
                extras["capacity"] = capacity
            if registered is not None and required:
                extras["registered"] = registered
            yield ctx.base(
                rid,
                title=title,
                description=desc,
                url=link or None,
                category=category,
                source_categories=cats,
                tags=[*p.get("tags", []), *(["registration_required"] if required else [])],
                start=start,
                end=end if end and end >= start and not all_day else None,
                all_day=all_day,
                location={
                    "venue_name": f"{label} – {branch}" if label and branch else branch,
                    "address": join_address(street, city, _text(loc, "state"), _text(loc, "zip")),
                    "lat": lat,
                    "lon": lon,
                    "geocode_method": "reported" if lat is not None else None,
                },
                organizer=label or ctx.source.name,
                price={"is_free": True} if says_free(title, desc) else {},
                availability=availability,
                extras=extras,
                _html=html,
            )


def _text(el: ET.Element | None, tag: str) -> str | None:
    if el is None:
        return None
    v = el.findtext(f"{BC}{tag}")
    return v.strip() if v and v.strip() else None


def _flag(el: ET.Element | None, tag: str) -> bool:
    return (_text(el, tag) or "").lower() == "true"


def _float(v: str | None) -> float | None:
    try:
        return float(v) if v else None
    except ValueError:
        return None


def _int(v: str | None) -> int | None:
    try:
        return int(v) if v else None
    except ValueError:
        return None
