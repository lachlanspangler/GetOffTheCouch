"""Galaxy Digital "Get Connected" volunteer portals (HandsOn Twin Cities, United Way of King County …).

    GET <base_url>/need/rss/                     RSS 2.0, the 15 newest needs — discovery only
    GET <base_url>/need/detail/?need_id=N        server-rendered need page — the record

The RSS items carry only title, link, pubDate and an HTML blurb (no date, place or organization), so we use the
feed to discover need ids and read each need's detail page, which has: the date line ("ongoing" /
"Until Dec 18, 2026"), time ("Flexible"), requirements ("Register by Nov 13, 2026", "Is Family Friendly",
"Virtual Opportunity", "18 and older"), the address, the nonprofit, and — for shift-based needs — a shift table
(Begins · Registration Closes · Duration · Open Spots "30 of 30").

How dates map (nothing invented):
  * shift rows → one record per shift (``max_shifts`` per need), start/end from "Fri Oct 16, 2026 @ 9:30am to
    11:15am", availability from open spots, ``registration.closes_at`` from the row's "Registration Closes";
  * "Until <date>" (no shifts) → an all-day record from the fetch date to that date, and
    ``registration.closes_at`` = that date 23:59 (method: extracted);
  * "ongoing" (no shifts) → an all-day record for the fetch date only, kind recurring — i.e. "listed as open
    today". It stays on the dashboard while the feed keeps listing it (the RSS is a 15-newest window, so
    snapshots are never ``complete`` and nothing is marked gone because it scrolled off the feed).

robots.txt: named SEO bots are blocked; ``User-agent: *`` has an empty Disallow (allowed). The RSS is parsed with
stdlib ``xml.etree``; documents with a DOCTYPE/ENTITY declaration are refused (no entity expansion).
The official API needs a per-tenant Bearer key — the upgrade path.

    params:
      base_url: https://handsontwincities.galaxydigital.com
      max_details: 15
      max_shifts: 6
"""

from __future__ import annotations

import html as htmllib
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import date, datetime, time
from typing import Any
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text
from gotc.http.client import HttpStatusError

_DATE = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+\d{4}"
_CLOCK = r"\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?"
_SHIFT = re.compile(
    rf"(?:[A-Z][a-z]{{2}}\s+)?({_DATE})\s*@\s*({_CLOCK})(?:\s*to\s*(?:({_DATE})\s*@\s*)?({_CLOCK}))?", re.I
)
_UNTIL = re.compile(rf"\bUntil\s+({_DATE})", re.I)
_REG_BY = re.compile(rf"\bRegister by\s+({_DATE})", re.I)
_THROUGH = re.compile(rf"({_DATE})\s+(?:through|thru|to|-|–)\s+({_DATE})", re.I)
_RANGE = re.compile(
    r"(?<![\d:])(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)?\s*(?:-|–|to)\s*(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)?(?![\d:])",
    re.I,
)


def need_ids_from_rss(content: bytes) -> list[str]:
    """Need ids in feed order. Refuses DTDs/entities (billion-laughs / external entities) before parsing."""
    head = content[:4096].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in content.upper():
        raise ValueError("Galaxy Digital RSS contains a DOCTYPE/ENTITY declaration — refusing to parse")
    root = ET.fromstring(content)
    ids: list[str] = []
    for item in root.iter("item"):
        for tag in ("link", "guid"):
            text = (item.findtext(tag) or "").strip()
            nid = (parse_qs(urlsplit(text).query).get("need_id") or [""])[0]
            if nid.isdigit():
                if nid not in ids:
                    ids.append(nid)
                break
    return ids


@register
class GalaxyDigitalAdapter(Adapter):
    name = "galaxydigital"

    def required_params(self) -> tuple[str, ...]:
        return ("base_url",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        base = str(ctx.params["base_url"]).rstrip("/")
        r = ctx.http.get(f"{base}/need/rss/")
        if b"<rss" not in r.content[:2000]:
            raise ValueError(f"{base}/need/rss/ is not an RSS feed (tenant moved or 'Bad Domain'?)")
        ids = need_ids_from_rss(r.content)
        payloads = [Payload.from_response(r, ctx.now, "xml")]
        for nid in ids[: int(ctx.params.get("max_details", 15))]:
            try:
                d = ctx.http.get(f"{base}/need/detail/", params={"need_id": nid})
            except HttpStatusError as e:
                if e.kind == "not_found":
                    continue  # need closed between the feed and the page: nothing to show
                raise
            if f"need_id={nid}" not in d.url:
                continue  # redirected to the listing: the need is no longer public
            payloads.append(Payload.from_response(d, ctx.now, "html", need_id=nid))
        return FetchResult(payloads, complete=False)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        if payload.content_type == "xml" or b"<rss" in payload.content[:2000]:
            return  # the feed is discovery only (see module docstring)
        nid = (parse_qs(urlsplit(payload.url).query).get("need_id") or [""])[0]
        if not nid and (m := re.search(r'data-need-id="(\d+)"', payload.text)):
            nid = m.group(1)  # payload stored without its URL (fixtures): the page names itself
        yield from _need(payload.text, nid, payload.url, ctx)


def _need(page: str, nid: str, url: str, ctx: ParseContext) -> Iterator[dict[str, Any]]:
    tz = ZoneInfo(ctx.city.timezone)
    h1 = re.search(r'<h1 class="panel-title[^"]*">(.*?)</h1>', page, re.S)
    title = clean_text(h1.group(1), 300) if h1 else None
    if not nid or not title:
        yield {"_reject": "need page without id/title", "_hint": url}
        return
    desc_m = re.search(
        r'<h2 class="section-header">Description</h2>\s*<div class="section-content[^"]*">(.*?)</div>', page, re.S
    )
    desc_html = desc_m.group(1) if desc_m else None
    desc = clean_text(desc_html, 4000)
    sec = re.search(r'<section class="address-time[^"]*">(.*?)</section>', page, re.S)
    when = [_txt(t) for t in re.findall(r'<td class="text[^"]*">(.*?)</td>', sec.group(1), re.S)] if sec else []
    reqs = [
        _txt(t) for t in re.findall(r'<tr class="requirement[^"]*"[^>]*>.*?<td class="text">(.*?)</td>', page, re.S)
    ]
    agency = re.search(r'<div class="agency[^"]*">.*?<div class="title">(.*?)</div>', page, re.S)
    org = clean_text(agency.group(1)) if agency else None
    addr_m = re.search(r'<tr class="address">.*?<td class="text">(.*?)</td>', page, re.S)
    address = _address(addr_m.group(1)) if addr_m else None
    virtual = any(r.lower() == "virtual opportunity" for r in reqs)
    reg_by = next((_day(m.group(1)) for r in reqs if (m := _REG_BY.search(r))), None)
    tags = ["family_friendly"] if any(r.lower() == "is family friendly" for r in reqs) else []
    if any(r.lower() == "is outdoors" for r in reqs):
        tags.append("outdoor")
    if any(r.lower() == "is wheelchair accessible" for r in reqs):
        tags.append("accessible")
    age = next((r for r in reqs if re.search(r"\band (older|younger)\b|\bages?\b", r, re.I)), None)
    signup = ["individual"] if "Respond" in page else []
    if "Respond as Team" in page:
        signup.append("team")
    cls = ctx.tax.classify(title, desc, default="volunteer.one_off")
    page_url = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}/need/detail/?need_id={nid}"
    common: dict[str, Any] = {
        "title": title,
        "description": desc,
        "url": page_url,
        "source_categories": [],
        "location": {} if virtual else {"address": address},
        "organizer": org,
        "tags": tags,
        "_html": desc_html,
    }
    extras_base = {"need_id": nid, "virtual": virtual, "age_requirement": age, "date_text": " · ".join(when) or None}

    shifts = _shifts(page, tz)
    if shifts:
        for sch, start, end, closes_raw, open_n, total_n in shifts[: int(ctx.params.get("max_shifts", 6))]:
            closes = _shift_close(closes_raw, tz)
            avail = "registration_open"
            if open_n is not None:
                avail = "waitlist" if open_n == 0 else ("few_left" if open_n <= 2 else "registration_open")
            if closes is not None and closes < ctx.fetched_at:
                avail = "registration_closed"
            category = cls.category if cls.category.startswith("volunteer.") else "volunteer.one_off"
            yield ctx.base(
                f"{nid}:{sch}",
                **common,
                kind="one_off",
                category=category,
                start=start,
                end=end,
                availability=avail,
                registration=_reg(page_url, closes, closes_raw, signup, "reported"),
                offers=[_offer(ctx, page_url, avail)],
                extras={**extras_base, "shift_id": sch, "spots_left": open_n, "spots_total": total_n},
            )
        return

    today = ctx.fetched_at.astimezone(tz).date()
    until = next((_day(m.group(1)) for w in when if (m := _UNTIL.search(w))), None)
    ongoing = any(re.fullmatch(r"(?:Get Connected Icon\s+)?ongoing", w, re.I) for w in when)
    span = next((m for w in when if (m := _THROUGH.search(w))), None)
    single = next((d for w in when if not _UNTIL.search(w) and (d := _day(w))), None)
    time_text = when[1] if len(when) > 1 else None
    start_t: time | None = None
    end_t: time | None = None
    if until is not None:
        start_d, end_d, kind = today, until, "one_off"
    elif span is not None and (d0 := _day(span.group(1))) and (d1 := _day(span.group(2))):
        start_d, end_d, kind = d0, d1, "one_off"
    elif single is not None:
        start_d, end_d, kind = single, single, "one_off"
        start_t, end_t = _time_range(time_text)
    elif ongoing:
        start_d, end_d, kind = today, today, "recurring"
    else:
        yield {"_reject": f"need without a date line ({' · '.join(when) or 'none'})", "_hint": f"{nid}: {title}"}
        return
    if end_d < start_d:
        yield {"_reject": f"need ended {end_d.isoformat()}", "_hint": f"{nid}: {title}"}
        return
    closes_d = reg_by or until
    closes = datetime.combine(closes_d, time(23, 59), tz) if closes_d else None
    evidence = next((r for r in reqs if _REG_BY.search(r)), None) or next((w for w in when if _UNTIL.search(w)), None)
    if kind == "recurring":
        category = cls.category if cls.category in ("volunteer.recurring", "volunteer.board") else "volunteer.recurring"
    else:
        category = cls.category if cls.category.startswith("volunteer.") else "volunteer.one_off"
    flexible = bool(time_text and re.search(r"\bflexible\b", time_text, re.I))
    avail = "registration_closed" if closes is not None and closes < ctx.fetched_at else "registration_open"
    timed = start_t is not None and end_t is not None
    yield ctx.base(
        nid,
        **common,
        kind=kind,
        category=category,
        start=datetime.combine(start_d, start_t if timed and start_t else time(0, 0), tz),
        end=datetime.combine(end_d, end_t if timed and end_t else time(23, 59), tz),
        all_day=not timed,
        recurrence=("Ongoing" + (" · flexible schedule" if flexible else "")) if ongoing else None,
        availability=avail,
        registration=_reg(page_url, closes, evidence, signup, "extracted" if closes else "reported"),
        offers=[_offer(ctx, page_url, avail)],
        extras={
            **extras_base,
            "time_text": time_text,
            "dates_basis": "listed as open on the fetch date" if kind == "recurring" or until else None,
        },
    )


def _time_range(text: str | None) -> tuple[time | None, time | None]:
    """'9am-1pm' / '10-12:30pm' / '4:30-6:00 pm' / 'Shifts between: 2:30pm - 9pm' → (start, end).
    Only a single unambiguous range counts ('12:45- 4:00 pm or 6:15-9:00 pm' → None: two shifts)."""
    if not text:
        return None, None
    ranges = _RANGE.findall(text)
    if len(ranges) != 1:
        return None, None
    h1, m1, ap1, h2, m2, ap2 = ranges[0]
    if not (ap1 or ap2):
        return None, None
    ap2 = (ap2 or ap1).lower()[0]
    end = _hm(int(h2), int(m2 or 0), ap2)
    if ap1:
        start = _hm(int(h1), int(m1 or 0), ap1.lower()[0])
    else:  # "10-12:30pm": same half-day as the end unless that puts the start after the end
        start = _hm(int(h1), int(m1 or 0), ap2)
        if start > end:
            start = _hm(int(h1), int(m1 or 0), "a")
    if end <= start:
        if not ranges[0][5] and end.hour < 12:  # "10:00am - 12:30": end without am/pm rolls to the afternoon
            end = _hm(int(h2), int(m2 or 0), "p")
        if end <= start:
            return None, None
    return start, end


def _hm(h: int, m: int, ap: str) -> time:
    if not (1 <= h <= 12 and 0 <= m < 60):
        return time(0, 0)
    return time(h % 12 + (12 if ap == "p" else 0), m)


def _txt(fragment: str) -> str:
    t = re.sub(r"<svg.*?</svg>", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", t))).replace("\xa0", " ").strip()


def _address(fragment: str) -> str | None:
    lines = [
        re.sub(r"\s+", " ", htmllib.unescape(x)).replace("\xa0", " ").strip() for x in re.split(r"<br\s*/?>", fragment)
    ]
    return ", ".join(dict.fromkeys(x for x in lines if x)) or None


def _day(text: str) -> date | None:
    m = re.search(_DATE, text, re.I)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(0).replace("Sept", "Sep").replace(".", ""), "%b %d, %Y").date()  # noqa: DTZ007
    except ValueError:
        return None


def _clock(s: str) -> time:
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*([ap])", s.strip(), re.I)
    assert m is not None
    return time(int(m.group(1)) % 12 + (12 if m.group(3).lower() == "p" else 0), int(m.group(2) or 0))


def _shifts(page: str, tz: ZoneInfo) -> list[tuple[str, datetime, datetime | None, str | None, int | None, int | None]]:
    table = re.search(r'<table id="shifts-table".*?<tbody>(.*?)</tbody>', page, re.S)
    if not table:
        return []
    out = []
    for row in re.findall(r"<tr>(.*?)</tr>", table.group(1), re.S):
        cells = [_txt(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        sch = re.search(r'data-sch-id="(\d+)"', row)
        m = _SHIFT.search(cells[0]) if cells else None
        if not m or not sch:
            continue
        d0 = _day(m.group(1))
        if d0 is None:
            continue
        start = datetime.combine(d0, _clock(m.group(2)), tz)
        end = None
        if m.group(4):
            d1 = _day(m.group(3)) if m.group(3) else d0
            end = datetime.combine(d1 or d0, _clock(m.group(4)), tz)
            if end < start:
                end = None
        spots = re.search(r"(\d+)\s+of\s+(\d+)", cells[3]) if len(cells) > 3 else None
        out.append(
            (
                sch.group(1),
                start,
                end,
                (cells[1] or None) if len(cells) > 1 else None,
                int(spots.group(1)) if spots else None,
                int(spots.group(2)) if spots else None,
            )
        )
    return out


def _shift_close(raw: str | None, tz: ZoneInfo) -> datetime | None:
    if not raw:
        return None
    m = _SHIFT.search(raw)
    if m and (d := _day(m.group(1))):
        return datetime.combine(d, _clock(m.group(2)), tz)
    d = _day(raw)
    return datetime.combine(d, time(23, 59), tz) if d else None


def _reg(url: str, closes: datetime | None, evidence: str | None, signup: list[str], method: str) -> dict[str, Any]:
    return {
        "closes_at": closes,
        "signup_types": signup,
        "url": url,
        "evidence": evidence if closes else None,
        "method": method,
        "confidence": 0.9 if closes else 1.0,
    }


def _offer(ctx: ParseContext, url: str, avail: str) -> dict[str, Any]:
    return {
        "seller": ctx.source.name,
        "kind": "registration",
        "url": url,
        "listing_count": None,
        "availability": avail,
        "source_id": ctx.source.id,
        "fetched_at": ctx.fetched_at,
    }
