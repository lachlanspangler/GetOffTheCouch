"""Challenge Entertainment — weekly live trivia, music bingo (Singo) and Pub Poll nights at bars.

    GET https://challengeentertainment.com/wp-json/ce/v1/shows      one JSON array, every show nationwide (~0.9 MB)

Access (checked 2026-10-16): robots.txt is Yoast's ``User-agent: * / Disallow:`` (everything allowed, including
``/wp-json/``). The site has no terms page (its page sitemap lists only the privacy policy, which has no
automation clause). ``ce/v1/shows`` is the undocumented JSON the site's own show finder loads, so it may change
without notice (grade C); the same data is exposed through the standard WordPress REST routes.

Each show: ``title`` ("Kelly’s Irish – W Oltorf St – Live Trivia"), ``link``, ``day`` ([1..7], **1 = Sunday**),
``time`` ("7:00 PM", local wall time), ``frequency`` (Weekly | Bi-Weekly | Monthly | 2x/month | 3x/month),
``next_date`` (YYYY-MM-DD), ``classes`` (``metro-<slug>``, ``game-<slug>``) and ``venue`` {name, street, city,
state, zipcode, latitude, longitude, phone, website}. The venue phone is never mapped.

Dates: ``next_date`` + ``time`` is **reported**. Weekly shows add the next three weeks and Bi-Weekly shows the
next three fortnights (**derived**, labeled in extras); Monthly / n×-per-month shows only get ``next_date``
(their rule can't be expanded reliably). When ``day`` disagrees with ``next_date`` (3 of 937 on 2026-10-16) we
trust ``next_date`` and don't expand. A ``next_date`` in the past is rolled forward on the show's own cadence.

City filter: ``metro-<slug>`` in ``params.metros`` *and* within ``max_km`` of the city center (default 2 × the
city radius) — the metro areas are large (Killeen is in "austin"). Filtered shows aren't rejects.

    params:
      url: https://challengeentertainment.com/wp-json/ce/v1/shows
      metros: [nashville]
"""

from __future__ import annotations

import html as htmllib
import json
import math
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from dateutil import parser as dtparser

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text, join_address

URL = "https://challengeentertainment.com/wp-json/ce/v1/shows"
N_DATES = 4
STEP = {"weekly": 7, "bi-weekly": 14}
_BINGO = {"xtreme-bar-bingo", "ballistic-bingo"}


@register
class ChallengeEntertainmentAdapter(Adapter):
    name = "challenge"

    def required_params(self) -> tuple[str, ...]:
        return ("metros",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        r = ctx.http.get(str(ctx.params.get("url", URL)))
        data = r.json()
        if not isinstance(data, list) or not data:
            raise ValueError("Challenge Entertainment shows: expected a non-empty JSON array")
        return FetchResult([Payload.from_response(r, ctx.now, "json")], complete=True)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        data = json.loads(payload.content)
        if not isinstance(data, list):
            yield {"_reject": "payload is not a JSON array", "_hint": payload.text[:200]}
            return
        metros = {f"metro-{m}" for m in ctx.params.get("metros") or []}
        max_km = float(ctx.params.get("max_km") or ctx.city.radius_km * 2)
        tz = ZoneInfo(ctx.city.timezone)
        today = ctx.fetched_at.astimezone(tz).date()
        for show in data:
            if not isinstance(show, dict):
                yield {"_reject": "show is not an object", "_hint": str(show)[:200]}
                continue
            classes = {str(c) for c in show.get("classes") or []}
            if not classes & metros:
                continue  # another market
            raw_venue = show.get("venue")
            venue: dict[str, Any] = raw_venue if isinstance(raw_venue, dict) else {}
            lat, lon = _f(venue.get("latitude")), _f(venue.get("longitude"))
            if lat is not None and lon is not None and _km((lat, lon), ctx.city.center) > max_km:
                continue  # in the metro but far from the city
            yield from _records(show, venue, lat, lon, classes, ctx, tz, today)


def _records(
    show: dict[str, Any],
    venue: dict[str, Any],
    lat: float | None,
    lon: float | None,
    classes: set[str],
    ctx: ParseContext,
    tz: ZoneInfo,
    today: date,
) -> Iterator[dict[str, Any]]:
    sid = show.get("id")
    raw_title = clean_text(htmllib.unescape(str(show.get("title") or "")))
    hint = f"{sid}: {raw_title}"
    try:
        nxt = date.fromisoformat(str(show.get("next_date")))
        at = dtparser.parse(str(show.get("time"))).time()
    except (ValueError, OverflowError):
        yield {"_reject": "show without a parseable next_date/time", "_hint": hint[:200]}
        return
    if not sid or not raw_title:
        yield {"_reject": "show without id/title", "_hint": hint[:200]}
        return
    freq = str(show.get("frequency") or "").strip().lower()
    step = STEP.get(freq)
    days = show.get("day") if isinstance(show.get("day"), list) else []
    agrees = not days or (nxt.isoweekday() % 7) + 1 in days  # 1 = Sunday … 7 = Saturday
    while step and nxt < today:  # stale next_date: roll forward on the show's own cadence
        nxt += timedelta(days=step)
    if nxt < today:
        return  # a monthly show whose next date already passed and can't be rolled: nothing to show
    dates = [nxt + timedelta(days=step * i) for i in range(N_DATES)] if step and agrees else [nxt]
    game_slug = next((c.removeprefix("game-") for c in sorted(classes) if c.startswith("game-")), "")
    label = raw_title.rsplit(" – ", 1)[-1].strip() if " – " in raw_title else "Trivia"
    vname = clean_text(htmllib.unescape(str(venue.get("name") or ""))) or raw_title.split(" – ")[0]
    category = "trivia_games.bingo" if game_slug in _BINGO else "trivia_games.trivia"
    when = f"{label} · {freq.title() if freq else 'Recurring'} on {nxt.strftime('%A')}s at {at.strftime('%-I:%M %p')}"
    region = " ".join(x for x in (venue.get("state"), venue.get("zipcode")) if x)
    url = show.get("link") if str(show.get("link") or "").startswith("http") else None
    for i, d in enumerate(dates):
        start = datetime.combine(d, at, tz)
        yield ctx.base(
            f"{sid}:{d.isoformat()}",
            title=f"{label} at {vname}",
            description=f"Challenge Entertainment {label.lower()} night at {vname}. {when}.",
            url=url,
            kind="recurring",
            category=category,
            source_categories=[game_slug] if game_slug else [],
            start=start,
            recurrence=f"{freq.title() if freq else 'Recurring'} · {nxt.strftime('%A')}s {at.strftime('%-I:%M %p')}",
            location={
                "venue_name": vname,
                "address": join_address(venue.get("street"), venue.get("city"), region),
                "lat": lat,
                "lon": lon,
                "geocode_method": "reported" if lat is not None else None,
            },
            organizer="Challenge Entertainment",
            availability="unknown",
            extras={
                "frequency": freq or None,
                "dates": "reported (next_date)" if i == 0 else f"derived: next_date + {(step or 0) * i} days",
                "day_mismatch": None if agrees else True,
            },
        )


def _f(v: Any) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) and not (abs(x) < 1e-6) else None


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))
