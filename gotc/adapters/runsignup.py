"""RunSignup "Get Races" REST API — upcoming races with registration periods (published deadlines).

    GET https://runsignup.com/Rest/races?format=json&events=T&zipcode=60602&radius=15
        &start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&sort=date+ASC&results_per_page=100&page=N

Docs: https://runsignup.com/API/races/GET . The Races method answers without a key, but the API Terms of Use
(https://runsignup.com/About-Us/APIDeveloper-Contract, checked 2026-10-16) say "You must register and agree to
these Terms before accessing the RunSignup API", and the API Keys page says "Register as an API caller to make
calls to the API". So the source is gated (``requires:`` in config/sources.yaml) on the free **API caller
registration** (``RUNSIGNUP_API_REG`` → ``rsu_api_reg`` GET param, ``RUNSIGNUP_API_REG_SECRET`` →
``X-RSU-API-REG-SECRET`` header), which only the user can create (it's tied to a RunSignup account).
Rate limit: at most 2 concurrent calls; we make sequential calls with ``min_interval_s`` between them.
robots: ``runsignup.com/robots.txt`` allows ``/Rest/`` (``api.runsignup.com/robots.txt`` is ``Disallow: /``,
so we never call that host).

**Design: one global source (scope all_cities).** Each city unit searches by ZIP + radius around the city
center (``params.zipcodes[<slug>]``; radius = the city's ``radius_km`` in miles unless ``radius_miles`` is set).

**Times.** Per the docs, "Event start and end times are in the timezone of the race. All other dates/times are
in Eastern Time" — so ``start_time`` is parsed in the race's ``timezone`` and every ``registration_opens`` /
``registration_closes`` in **America/New_York**.

**Mapping (one record per race, its next date).**
  * start = the earliest event ``start_time`` on ``next_date`` (else ``next_date``, all day)
  * price = cheapest / dearest ``race_fee`` over registration periods that haven't closed (+ processing fee note)
  * registration (method ``reported``): ``opens_at`` = earliest period open, ``closes_at`` = latest period close,
    ``early_bird_ends_at`` = close of the first still-open period when a later period costs more
  * signup_types: individual, plus team when an event looks like a relay/team event
  * availability: registration_open / registration_closed (``is_registration_open`` + period dates)
  * category fitness.race; races whose name says club run / group run → fitness.run_club
  * private, draft, virtual-only and already-started (multi-week series, add-on store pages) races are skipped
    (not rejected); ``postponed_cancelled_text`` marks a race cancelled/postponed
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from gotc.adapters.base import Adapter, AdapterConfigError, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text, join_address, money

BASE = "https://runsignup.com/Rest/races"
ET = ZoneInfo("America/New_York")  # RunSignup: "All other dates/times are in Eastern Time"
_TEAM = re.compile(r"(?i)\b(relay|team|teams|duo|pairs?|tandem|corporate challenge)\b")
_CLUB = re.compile(r"(?i)\b(run club|running club|group run|social run|club run|weekly run)\b")
_VIRTUAL = re.compile(r"(?i)virtual")


@register
class RunSignupAdapter(Adapter):
    name = "runsignup"

    def required_params(self) -> tuple[str, ...]:
        return ("zipcodes",)

    def fetch(self, ctx: FetchContext) -> FetchResult:
        self.check_config(ctx.source)
        p = ctx.params
        zipcode = (p.get("zipcodes") or {}).get(ctx.city.slug)
        if not zipcode:
            raise AdapterConfigError(f"{ctx.source.id}: no params.zipcodes entry for {ctx.city.slug}")
        today = ctx.now.astimezone(ZoneInfo(ctx.city.timezone)).date()
        radius = int(p.get("radius_miles") or max(5, round(ctx.city.radius_km / 1.609)))
        per_page = int(p.get("results_per_page", 100))
        max_pages = int(p.get("max_pages", 5))
        q: dict[str, str | int] = {
            "format": "json",
            "events": "T",
            "include_extra_date_info": "T",
            "zipcode": str(zipcode),
            "radius": radius,
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=int(p.get("horizon_days", 120)))).isoformat(),
            "sort": "date ASC",
            "results_per_page": per_page,
        }
        headers: dict[str, str] = {}
        if reg := ctx.settings.secret("RUNSIGNUP_API_REG"):
            q["rsu_api_reg"] = reg
            headers["X-RSU-API-REG-SECRET"] = ctx.settings.secret("RUNSIGNUP_API_REG_SECRET") or ""
        payloads: list[Payload] = []
        complete = True
        for page in range(1, max_pages + 1):
            r = ctx.http.get(str(p.get("url", BASE)), params={**q, "page": page}, headers=headers)
            data = r.json()
            if not isinstance(data, dict) or "error" in data:
                err = data.get("error") if isinstance(data, dict) else data
                raise ValueError(f"RunSignup error: {str(err)[:300]}")
            races = data.get("races")
            if not isinstance(races, list):
                raise ValueError("RunSignup response has no 'races' list — API changed?")
            payloads.append(Payload.from_response(r, ctx.now, "json", page=page, zipcode=zipcode, radius=radius))
            if len(races) < per_page:
                break
        else:
            complete = False
        return FetchResult(payloads, complete=complete)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        data = json.loads(payload.content)
        races = data.get("races") if isinstance(data, dict) else None
        if not isinstance(races, list):
            yield {"_reject": "payload has no races list", "_hint": payload.text[:200]}
            return
        for item in races:
            race = item.get("race") if isinstance(item, dict) else None
            if not isinstance(race, dict):
                yield {"_reject": "race entry is not an object", "_hint": str(item)[:200]}
                continue
            rec = _race(race, ctx)
            if rec is not None:
                yield rec


def _et(value: Any) -> datetime | None:
    """'11/25/2026 18:00' (Eastern Time per the API docs) → aware datetime."""
    return _mdy(value, ET)


def _mdy(value: Any, tz: ZoneInfo) -> datetime | None:
    s = str(value or "").strip()
    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=tz)
        except ValueError:
            continue
    return None


def _race(race: dict[str, Any], ctx: ParseContext) -> dict[str, Any] | None:
    rid = race.get("race_id")
    name = clean_text(race.get("name"), 300)
    hint = f"{rid}: {name}"
    if race.get("is_private_race") == "T" or race.get("is_draft_race") == "T":
        return None  # not public — skipped, like an out-of-city record
    try:
        race_tz = ZoneInfo(str(race.get("timezone") or ctx.city.timezone))
    except (KeyError, ValueError):
        race_tz = ZoneInfo(ctx.city.timezone)
    next_d = _mdy(race.get("next_date"), race_tz)
    if not rid or not name or next_d is None:
        return {"_reject": "race without id, name or next_date", "_hint": hint[:200]}
    events = [e for e in race.get("events") or [] if isinstance(e, dict)]
    if events and all(_VIRTUAL.search(str(e.get("event_type") or "")) for e in events):
        return None  # virtual-only: nowhere to go (normalize.location_skip would skip it anyway)
    in_person = [e for e in events if not _VIRTUAL.search(str(e.get("event_type") or ""))]
    day = next_d.date()
    if day < ctx.fetched_at.astimezone(race_tz).date():
        # next_date already passed: a multi-week series or an add-on store page ("Add-On Purchases") whose
        # window is still open. Not a dated race we can show — skipped, like an out-of-city record.
        return None
    starts = sorted(
        dt for e in in_person if (dt := _mdy(e.get("start_time"), race_tz)) is not None and dt.date() == day
    )
    end_d = _mdy(race.get("next_end_date"), race_tz)
    all_day = not starts
    start = starts[0] if starts else datetime.combine(day, time(0, 0), race_tz)
    end = None
    if end_d is not None and end_d.date() > day:
        end = datetime.combine(end_d.date(), time(23, 59), race_tz)
    elif all_day:
        end = datetime.combine(day, time(23, 59), race_tz)

    now = ctx.fetched_at
    periods = [
        (o, c, money(per.get("race_fee")), money(per.get("processing_fee")))
        for e in in_person
        for per in e.get("registration_periods") or []
        if isinstance(per, dict)
        for o, c in [(_et(per.get("registration_opens")), _et(per.get("registration_closes")))]
    ]
    live = [x for x in periods if x[1] is None or x[1] >= now]
    fees = [f for _, _, f, _ in live if f is not None]
    proc = [pf for _, _, f, pf in live if f is not None and pf]
    price: dict[str, Any] = {}
    if fees:
        paid = [f for f in fees if f > 0]
        if not paid:
            price = {"is_free": True}
        else:  # a free kids' dash or guide entry isn't the price a newcomer pays: cheapest *paid* entry
            notes = ["+ processing fee" if proc else None, "some entries free" if len(paid) < len(fees) else None]
            price = {"min": min(paid), "max": max(paid), "note": "; ".join(n for n in notes if n) or None}

    opens = min((o for o, _, _, _ in periods if o), default=None)
    closes = max((c for _, c, _, _ in periods if c), default=None)
    early = min(
        (eb for e in in_person if (eb := _early_bird(e, now)) is not None and (closes is None or eb < closes)),
        default=None,
    )
    team = any(_TEAM.search(f"{e.get('name') or ''} {e.get('event_type') or ''}") for e in in_person)
    open_flag = race.get("is_registration_open") == "T"
    is_open = open_flag and (closes is None or closes >= now) and (opens is None or opens <= now)
    availability = "registration_open" if is_open else "registration_closed"
    if opens is not None and opens > now:
        availability = "not_yet_on_sale"
    notice = clean_text(race.get("postponed_cancelled_text")) or ""
    if re.search(r"(?i)\bcancel+ed\b", notice):
        availability = "cancelled"
    elif re.search(r"(?i)\bpostponed\b", notice):
        availability = "postponed"

    url = race.get("url") if str(race.get("url") or "").startswith("http") else None
    evidence = None
    if closes:
        evidence = f"RunSignup registration period closes {closes.strftime('%b %-d, %Y %-I:%M %p')} ET"
        if early:
            evidence += f"; the first price tier ends {early.strftime('%b %-d %-I:%M %p')} ET"
    registration = None
    if periods or url:
        registration = {
            "opens_at": opens,
            "closes_at": closes,
            "early_bird_ends_at": early,
            "signup_types": ["individual", "team"] if team else ["individual"],
            "url": url,
            "evidence": evidence,
            "method": "reported",
            "confidence": 1.0 if closes else 0.8,
        }
    offers = []
    if url:
        offers.append(
            {
                "seller": "RunSignup",
                "kind": "registration",
                "url": url,
                "price_min": price.get("min"),
                "price_max": price.get("max"),
                "availability": availability,
                "fees_included": False if proc else None,
                "source_id": ctx.source.id,
                "fetched_at": ctx.fetched_at,
            }
        )
    raw_addr = race.get("address")
    addr: dict[str, Any] = raw_addr if isinstance(raw_addr, dict) else {}
    street, street2 = clean_text(addr.get("street")), clean_text(addr.get("street2"))
    # RunSignup's "street" is often a venue name ("Christ the King School Gymnasium") with the street in street2
    venue = street if street and street2 and not re.match(r"^\d", street) else None
    address = join_address(street2 if venue else street, None if venue else street2, addr.get("city"))
    if address and addr.get("state"):
        address = f"{address}, {addr.get('state')} {addr.get('zipcode') or ''}".strip()
    lines = [_event_line(e, race_tz) for e in in_person[:12]]
    desc = clean_text(race.get("description"), 1500)
    events_line = "Events: " + "; ".join(x for x in lines if x) if lines else None
    desc = "\n".join(filter(None, [notice or None, events_line, desc])) or None
    category = "fitness.run_club" if _CLUB.search(name) else "fitness.race"
    return ctx.base(
        f"{rid}:{day.isoformat()}",
        title=name,
        description=desc,
        url=url,
        kind="one_off",
        category=category,
        source_categories=sorted({str(e.get("event_type")) for e in in_person if e.get("event_type")}),
        start=start,
        end=end,
        all_day=all_day,
        timezone=str(race_tz.key),
        location={"venue_name": venue, "address": address},
        organizer=None,
        price=price,
        offers=offers,
        registration=registration,
        availability=availability,
        extras={
            "race_id": int(rid) if str(rid).isdigit() else str(rid),
            "external_race_url": race.get("external_race_url") or None,
            "events": len(in_person),
        },
        _html=None,
    )


def _early_bird(event: dict[str, Any], now: datetime) -> datetime | None:
    """The close of an event's earliest still-open price tier, when its next tier costs more (a real price step)."""
    tiers = sorted(
        (c, f)
        for per in event.get("registration_periods") or []
        if isinstance(per, dict)
        and (c := _et(per.get("registration_closes"))) is not None
        and c >= now
        and (f := money(per.get("race_fee"))) is not None
    )
    if len(tiers) < 2 or tiers[1][1] <= tiers[0][1]:
        return None
    return tiers[0][0]


def _event_line(e: dict[str, Any], tz: ZoneInfo) -> str:
    """'5K Run - Adult · 3.1 Miles · 9:00 AM'."""
    s = _mdy(e.get("start_time"), tz)
    parts = (clean_text(e.get("name")), clean_text(e.get("distance")), s.strftime("%-I:%M %p") if s else None)
    return " · ".join(x for x in parts if x)
