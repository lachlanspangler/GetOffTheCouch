"""Team Trivia (teamtrivia.com) — weekly pub trivia / music bingo nights, from public venue pages.

    GET https://www.teamtrivia.com/trivia-in-<region>/     region page: every venue in the market (links)
    GET https://www.teamtrivia.com/venue/<venue-slug>      venue page: schedule table + schema.org JSON-LD

Access (checked 2026-10-16): robots.txt disallows only admin/system paths and the zip-code gate's helpers
(``/getlocation.php``, ``/enter-site.php`` …); the region and venue pages are allowed **and listed in the
site's own sitemap** (``sitemap-locations.php``, ``sitemap-venues.php``). We never touch the gate, so the
"where to play" finder (``getlocation.php``) is not used. The venue pages publish schema.org ``Event`` JSON-LD
(the next four dated games, with correct UTC offsets across DST) and ``LocalBusiness`` geo. The site's /terms
page sits behind the zip-code gate (every gated URL returns the gate to a cookieless client), so no terms could
be read; nothing on the public pages restricts reuse. Requests are few (one region page + one page per venue,
every 48 h, ≥ 3 s apart).

Records: one per dated game night (kind ``recurring``, category ``trivia_games.trivia``; music bingo and Team
Feud are game nights too). Dates come from the JSON-LD (**reported**). If a venue page has a schedule table but
no JSON-LD events, the weekly rows ("Wednesdays · 7:00 PM · Team Trivia") are expanded to the next 4 dates
(``common.weekly_occurrences``, labeled ``dates: derived from the weekly schedule`` in extras). Free to play
(the page says "free to play, with no signup" and the JSON-LD says ``isAccessibleForFree``). The venue phone
number is never mapped.

    params:
      base_url: https://www.teamtrivia.com
      regions: {denver: denver}         # city slug → trivia-in-<region>
      max_venues: 60
"""

from __future__ import annotations

import html as htmllib
import json
import re
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from gotc.adapters.base import Adapter, AdapterConfigError, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text, join_address, weekly_occurrences

BASE = "https://www.teamtrivia.com"
_VENUE_LINK = re.compile(r'href="(https://www\.teamtrivia\.com/venue/[a-z0-9-]+)"')
_LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
_PANEL = re.compile(r"Game night.*?<tbody>(.*?)</tbody>", re.S)
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_DAYS = {d: i for i, d in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"])}
N_DATES = 4


@register
class TeamTriviaAdapter(Adapter):
    name = "teamtrivia"

    def required_params(self) -> tuple[str, ...]:
        return ("regions",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        region = (p.get("regions") or {}).get(ctx.city.slug)
        if not region:
            raise AdapterConfigError(f"{ctx.source.id}: no params.regions entry for {ctx.city.slug}")
        base = str(p.get("base_url", BASE)).rstrip("/")
        page = ctx.http.get(f"{base}/trivia-in-{region}/")
        venues = list(dict.fromkeys(_VENUE_LINK.findall(page.text)))
        if "Bar Trivia in" not in page.text:
            raise ValueError(f"trivia-in-{region}: not a region page — layout changed?")
        max_venues = int(p.get("max_venues", 60))
        payloads = [
            Payload.from_response(ctx.http.get(v), ctx.now, "html", venue=v.rsplit("/", 1)[-1])
            for v in venues[:max_venues]
        ]
        return FetchResult(payloads, complete=len(venues) <= max_venues)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        text = payload.text
        slug = urlsplit(payload.url).path.rstrip("/").rsplit("/", 1)[-1]
        blocks = [b for b in (_json(m) for m in _LD.findall(text)) if b is not None]
        place = next((b for b in blocks if b.get("@type") == "LocalBusiness"), {})
        events = [
            e for b in blocks for e in (b.get("@graph") or []) if isinstance(e, dict) and e.get("@type") == "Event"
        ]
        schedule = _schedule(text)
        if not place and not events:
            yield {"_reject": "venue page without schema.org LocalBusiness/Event JSON-LD", "_hint": slug}
            return
        loc = _location(place or (events[0].get("location") if events else {}) or {})
        name = clean_text(place.get("name")) or loc.get("venue_name") or slug
        now = ctx.fetched_at
        recs: list[dict[str, Any]] = []
        for e in events:
            start = _iso(e.get("startDate"))
            if start is None:
                recs.append({"_reject": "event without a parseable startDate", "_hint": f"{slug}: {e.get('name')}"})
                continue
            game = (clean_text(e.get("name")) or "").split(" at ")[0].lower()
            days = {d for d, _, g in schedule if g.lower() == game}
            if days and start.astimezone(ZoneInfo(ctx.city.timezone)).weekday() not in days:
                # seen live 2026-10-16: a Thursday game's "tonight" entry stamped with Friday's date (the site's
                # server had already rolled over to the next day). The schedule table is the tie-breaker.
                when = ", ".join(sorted(_day_name(d) + "s" for d in days))
                recs.append(
                    {"_reject": f"JSON-LD date {start.date()} is not on the posted schedule ({when})", "_hint": slug}
                )
                continue
            recs.append(self._record(ctx, slug, e.get("name"), start, name, loc, schedule, e, payload.url))
        if not events and schedule:  # no dated JSON-LD: expand the weekly table (derived dates)
            for day, at, game in schedule:
                for start in weekly_occurrences(day, at, ctx.city.timezone, now, N_DATES):
                    rec = self._record(ctx, slug, f"{game} at {name}", start, name, loc, schedule, {}, payload.url)
                    rec["extras"]["dates"] = "derived from the weekly schedule"
                    recs.append(rec)
        kept: dict[str, int] = {}
        for rec in sorted(recs, key=lambda r: str(r.get("start", ""))):
            if "_reject" in rec:
                yield rec
                continue
            if rec["start"] < now - timedelta(hours=3):
                continue  # already over
            game = rec["title"]
            if kept.get(game, 0) >= N_DATES:
                continue
            kept[game] = kept.get(game, 0) + 1
            yield rec

    def _record(
        self,
        ctx: ParseContext,
        slug: str,
        title: Any,
        start: datetime,
        venue: str,
        loc: dict[str, Any],
        schedule: list[tuple[int, str, str]],
        ev: dict[str, Any],
        url: str,
    ) -> dict[str, Any]:
        title_s = clean_text(title) or f"Team Trivia at {venue}"
        game = title_s.split(" at ")[0]
        rule = next((r for r in schedule if r[2].lower() == game.lower() and r[0] == start.weekday()), None)
        recurrence = f"{_day_name(rule[0])}s {rule[1]}" if rule else f"{_day_name(start.weekday())}s"
        status = str(ev.get("eventStatus") or "")
        availability = "free_no_ticket"
        if status.endswith("EventCancelled"):
            availability = "cancelled"
        elif status.endswith("EventPostponed"):
            availability = "postponed"
        free = ev.get("isAccessibleForFree", True) is not False
        return ctx.base(
            f"{slug}:{start.isoformat()}",
            title=title_s,
            description=clean_text(ev.get("description"))
            or f"Team Trivia {game.lower()} night at {venue}. Free to play; teams of any size, no signup.",
            url=ev.get("url") if str(ev.get("url") or "").startswith("http") else url,
            kind="recurring",
            category="trivia_games.trivia",
            source_categories=[game],
            tags=[],
            start=start,
            recurrence=recurrence,
            location=loc,
            organizer="Team Trivia",
            price={"is_free": True} if free else {},
            availability=availability,
            extras={"venue_page": url},
        )


def _json(raw: str) -> dict[str, Any] | None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _iso(v: Any) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(v))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else None


def _location(place: dict[str, Any]) -> dict[str, Any]:
    a, g = place.get("address"), place.get("geo")
    addr: dict[str, Any] = a if isinstance(a, dict) else {}
    geo: dict[str, Any] = g if isinstance(g, dict) else {}
    lat, lon = geo.get("latitude"), geo.get("longitude")
    ok = isinstance(lat, int | float) and isinstance(lon, int | float)
    region = " ".join(x for x in (addr.get("addressRegion"), addr.get("postalCode")) if x)
    return {
        "venue_name": clean_text(place.get("name")),
        "address": join_address(addr.get("streetAddress"), addr.get("addressLocality"), region),
        "lat": float(lat) if ok and lat is not None else None,
        "lon": float(lon) if ok and lon is not None else None,
        "geocode_method": "reported" if ok else None,
    }


def _schedule(text: str) -> list[tuple[int, str, str]]:
    """The 'Game night at …' table → [(weekday Mon=0, '7:00 PM', 'Team Trivia'), …]."""
    m = _PANEL.search(text)
    if not m:
        return []
    out: list[tuple[int, str, str]] = []
    for row in _ROW.findall(m.group(1)):
        cells = [clean_text(htmllib.unescape(c)) or "" for c in _TD.findall(row)]
        if len(cells) < 3:
            continue
        day = re.match(r"(?i)(monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?\b", cells[0])
        at = re.search(r"(?i)\b\d{1,2}:\d{2}\s*[ap]m\b", cells[1])
        if (
            day
            and at
            and not re.search(r"(?i)\b(1st|2nd|3rd|4th|first|second|third|last|other|every other)\b", cells[0])
        ):
            out.append((_DAYS[day.group(1).lower()], at.group(0).upper(), cells[2]))
    return out


def _day_name(i: int) -> str:
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][i]
