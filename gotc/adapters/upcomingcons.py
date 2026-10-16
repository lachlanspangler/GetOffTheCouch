"""UpcomingCons listing pages (anime / comic / gaming / sci-fi conventions) — schema.org ``Event`` microdata.

    GET https://www.upcomingcons.com/<category-page>      e.g. /anime-cons, /comic-conventions

robots.txt is empty (comments only) and /terms has no scraping clause (research 2026-10-15; robots re-checked
2026-10-16). Each listing is ``<div itemscope itemtype="http://schema.org/Event">`` with ``name``, ``url``
(UpcomingCons' own page — the list never links the official site, so neither do we), ``addressLocality`` /
``addressRegion`` and ``startDate``/``endDate`` meta tags. Detail pages can show stale editions; we only read lists.

**Design: one global source (scope all_cities)**, not one entry per city: the pages are national, so each city
unit fetches the same few pages (weekly, conditional GET) and keeps only cons whose locality is the city or one of
its ``aliases`` (or ``extra_localities[<city slug>]``, e.g. Rosemont for Chicago) *and* whose state matches.
Out-of-city cons are filtered, not rejected (they're valid, just not ours) — like a server-side ``?city=`` filter.

Category: taxonomy keywords on the con's name (niche.* only), else the parent ``niche`` ("Cons, faires & niche").
We do NOT use the page a con was listed on: the category pages are unreliable — on 2026-10-16 the same client got
the anime list back for /gaming-conventions and /science-fiction-conventions within one minute (headings correct,
lists not), and /furry-conventions mirrored /comic-conventions. So the pages are just a union for coverage
(deduped by listing id). Community-entered data: cross-check against the official site before curating.

    params:
      pages: [anime-cons, comic-conventions, gaming-conventions, science-fiction-conventions]
      extra_localities: {chicago: [Rosemont, Schaumburg]}
"""

from __future__ import annotations

import html as htmllib
import re
from collections.abc import Iterator
from datetime import date, datetime, time
from typing import Any
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text, us_state_code

BASE = "https://www.upcomingcons.com"
DEFAULT_PAGES = ["anime-cons", "comic-conventions", "gaming-conventions", "science-fiction-conventions"]
_BLOCK = re.compile(r'<div id="upcomingcon_(\d+)"[^>]*itemtype="https?://schema\.org/Event"[^>]*>', re.I)
_PROP = re.compile(r'itemprop="(name|addressLocality|addressRegion)"[^>]*>([^<]*)<', re.I)
_META = re.compile(r'<meta\s+itemprop="(startDate|endDate)"\s+content="([^"]*)"', re.I)
_URL = re.compile(r'<a\s+itemprop="url"\s+href="([^"]+)"', re.I)
_COUNTRIES = {"usa", "us", "united states", "united states of america", "u.s.", "u.s.a."}


@register
class UpcomingConsAdapter(Adapter):
    name = "upcomingcons"

    def fetch(self, ctx: FetchContext) -> FetchResult:
        base = str(ctx.params.get("base_url", BASE)).rstrip("/")
        payloads: list[Payload] = []
        for path in ctx.params.get("pages") or DEFAULT_PAGES:
            r = ctx.http.get(f"{base}/{str(path).strip('/')}")
            if not _BLOCK.search(r.text):
                raise ValueError(f"{path}: no schema.org Event blocks — UpcomingCons layout changed?")
            payloads.append(Payload.from_response(r, ctx.now, "html", page=path))
        return FetchResult(payloads, complete=True)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        path = urlsplit(payload.url).path.strip("/")
        names = _local_names(ctx)
        tz = ZoneInfo(ctx.city.timezone)
        text = payload.text
        blocks = list(_BLOCK.finditer(text))
        for i, m in enumerate(blocks):
            chunk = text[m.end() : blocks[i + 1].start() if i + 1 < len(blocks) else len(text)]
            cid = m.group(1)
            props = {k: clean_text(htmllib.unescape(v)) for k, v in _PROP.findall(chunk)}
            metas = dict(_META.findall(chunk))
            locality, state = _place(props.get("addressLocality"), props.get("addressRegion"))
            if state != ctx.city.state or (locality or "").lower() not in names:
                continue  # another city's con (see module docstring) — filtered, not rejected
            name = props.get("name")
            start_d, end_d = _date(metas.get("startDate")), _date(metas.get("endDate"))
            if not name or start_d is None:
                yield {"_reject": "con without name/startDate", "_hint": cid}
                continue
            if end_d is not None and end_d < start_d:
                end_d = None
            href = _URL.search(chunk)
            cls = ctx.tax.classify(name)
            by_name = cls.category.startswith("niche.")
            category = cls.category if by_name else "niche"
            dm = re.search(r'class="date"[^>]*>\s*([^<]+)', chunk)
            yield ctx.base(
                cid,
                title=name,
                url=urljoin(BASE + "/", href.group(1)) if href else None,
                kind="one_off",
                category=category,
                source_categories=[path],
                start=datetime.combine(start_d, time(0, 0), tz),
                end=datetime.combine(end_d or start_d, time(23, 59), tz),
                all_day=True,
                location={"address": f"{locality}, {state}"},
                availability="unknown",
                extras={
                    "listing_dates": clean_text(dm.group(1)) if dm else None,
                    "listing_page": payload.url,
                    "community_listing": True,
                    "classified_by": f"name: {cls.matched}" if by_name else "none (generic con)",
                },
            )


def _local_names(ctx: ParseContext) -> set[str]:
    extra: dict[str, list[str]] = ctx.params.get("extra_localities") or {}
    names = [ctx.city.name, *ctx.city.aliases, *extra.get(ctx.city.slug, [])]
    return {n.strip().lower() for n in names if n and n.strip()}


def _place(locality: str | None, region: str | None) -> tuple[str | None, str | None]:
    """('Minneapolis','MN') → as is; ('San Diego, California','United States') → ('San Diego','CA')."""
    loc = (locality or "").strip().rstrip(",")
    reg = (region or "").strip()
    state = us_state_code(reg)
    if state is None and "," in loc:
        head, _, tail = loc.rpartition(",")
        if (code := us_state_code(tail)) and (reg.lower() in _COUNTRIES or not reg):
            return head.strip(), code
    if state is None:
        return loc or None, None
    return loc or None, state


def _date(v: str | None) -> date | None:
    try:
        return date.fromisoformat(v) if v else None
    except ValueError:
        return None
