"""Curated registry: hand-verified leagues, cons, faires, run clubs — things with no API.

    config/registry/<city>.yaml   (a list of entries; schema = CuratedEntry below)

Honesty rules, enforced by the schema:
  * every entry carries ``evidence`` (a VERBATIM quote from ``source_url``) and ``verified_at``
  * nothing is typed in that the page didn't say — dates/prices missing on the page stay missing

Page-watch (self-verification): on each fetch we re-download every ``source_url`` (politely, robots-aware)
and check that the evidence quote is *still on the page*. If it is, the entry counts as re-verified today
(``fetched_at`` = now). If the page changed, the card is flagged "organizer page changed since we checked"
and its freshness clock stops at ``verified_at`` so it goes stale instead of silently lying. If the page
can't be fetched (403/Cloudflare), the entry stays valid until its SLA expires, then shows stale.

Recurring schedules ("every Tuesday 6pm") are expanded into the next few dates — labeled as derived
from the published schedule.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from gotc.adapters.base import Adapter, FetchContext, FetchResult, ParseContext, Payload, register
from gotc.adapters.common import clean_text
from gotc.http.client import FetchError
from gotc.schema import EventKind, SignupType, SkillLevel
from gotc.settings import CONFIG_DIR

_DAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CuratedRegistration(_M):
    opens: date | datetime | None = None
    closes: date | datetime | None = None
    early_bird_ends: date | datetime | None = None
    signup_types: list[SignupType] = Field(default_factory=list)
    skill_levels: list[SkillLevel] = Field(default_factory=list)
    url: HttpUrl | None = None
    status: Literal["open", "closed", "waitlist", "not_yet"] | None = None


class Weekly(_M):
    days: list[Literal["MO", "TU", "WE", "TH", "FR", "SA", "SU"]]
    at: str = Field(pattern=r"^\d{1,2}:\d{2}$")
    duration_min: int = 90
    occurrences: int = 4


class CuratedEntry(_M):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str
    category: str
    kind: EventKind = EventKind.ONE_OFF
    start: date | datetime | None = None  # local time if datetime; date → all-day unless `at` given
    end: date | datetime | None = None
    at: str | None = Field(default=None, pattern=r"^\d{1,2}:\d{2}$")
    weekly: Weekly | None = None
    recurrence: str | None = None
    venue: str | None = None
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    organizer: str | None = None
    url: HttpUrl | None = None
    description: str | None = None
    free: bool = False
    price_min: float | None = None
    price_max: float | None = None
    price_note: str | None = None
    registration: CuratedRegistration | None = None
    tags: list[str] = Field(default_factory=list)
    evidence: str = Field(min_length=12)
    source_url: HttpUrl
    verified_at: date
    watch: bool = True


def registry_path(city: str) -> Any:
    return CONFIG_DIR / "registry" / f"{city}.yaml"


def evidence_present(evidence: str, page_text: str) -> bool:
    """Every fragment of the quote ('…' / '...' separate elisions) must appear in the page text.

    Comparison is on lowercase alphanumerics only, so markup that splits words (drop-caps: "S<span>herwood"),
    whitespace, punctuation and curly-vs-straight quotes can't cause false "page changed" alarms.
    """
    norm = _compact(page_text)
    frags = [f.strip() for f in re.split(r"\.\.\.|…", evidence) if len(_compact(f)) >= 8]
    return bool(frags) and all(_compact(f) in norm for f in frags)


def _compact(s: str) -> str:
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    return re.sub(r"[^a-z0-9]+", "", s.lower())


@register
class CuratedAdapter(Adapter):
    name = "curated"

    def fetch(self, ctx: FetchContext) -> FetchResult:
        """One bundled payload {registry, pages{url: text|null}} so parse stays pure and replayable."""
        path = ctx.params.get("path") or registry_path(ctx.city.slug)
        registry = Path(path).read_text(encoding="utf-8")
        pages: dict[str, str | None] = {}
        errors: dict[str, str] = {}
        if ctx.params.get("watch", True):
            for u in sorted({str(e.source_url) for e in _entries(registry.encode()) if e.watch}):
                try:
                    pages[u] = ctx.http.get(u).text
                except FetchError as err:  # unverifiable today: not a unit failure; the entry ages toward stale
                    pages[u] = None
                    errors[u] = err.kind
        bundle = json.dumps({"registry": registry, "pages": pages, "errors": errors}).encode()
        return FetchResult([Payload(f"curated://{ctx.city.slug}", 200, bundle, ctx.now, "json")], complete=True)

    def parse(self, payload: Payload, ctx: ParseContext) -> Iterator[dict[str, Any]]:
        bundle = json.loads(payload.content)
        pages: dict[str, str | None] = bundle.get("pages", {})
        tz = ZoneInfo(ctx.city.timezone)
        try:
            entries = _entries(bundle["registry"].encode())
        except Exception as exc:
            yield {"_reject": f"registry YAML invalid: {exc}", "_hint": payload.url}
            return
        for e in entries:
            verified = datetime.combine(e.verified_at, time(12, 0), tz)
            page = pages.get(str(e.source_url))
            page_state = "unchecked"
            fetched_at = verified
            if page is not None:
                if evidence_present(e.evidence, page):
                    page_state, fetched_at = "evidence_present", ctx.fetched_at
                else:
                    page_state = "page_changed"
            starts = _starts(e, ctx.fetched_at.astimezone(tz), tz)
            if not starts:
                yield {"_reject": "entry has no start (and no weekly schedule)", "_hint": e.id}
                continue
            for start, end, all_day in starts:
                reg = None
                if e.registration:
                    r = e.registration
                    reg = {
                        "opens_at": _dt(r.opens, tz, time(0, 0)),
                        "closes_at": _dt(r.closes, tz, time(23, 59)),
                        "early_bird_ends_at": _dt(r.early_bird_ends, tz, time(23, 59)),
                        "signup_types": r.signup_types,
                        "skill_levels": r.skill_levels,
                        "url": r.url,
                        "evidence": e.evidence[:300],
                        "method": "curated",
                        "confidence": 0.9 if page_state != "page_changed" else 0.5,
                    }
                avail = {
                    "open": "registration_open",
                    "closed": "registration_closed",
                    "waitlist": "waitlist",
                    "not_yet": "not_yet_on_sale",
                }.get(e.registration.status if e.registration and e.registration.status else "", "unknown")
                if e.free and avail == "unknown":
                    avail = "free_no_ticket"
                desc = e.description or ""
                if page_state == "page_changed":
                    desc = (desc + "\n\n" if desc else "") + (
                        f"⚠️ The organizer's page changed since we verified this on {e.verified_at:%b %-d}. Check their site before relying on it."
                    )
                offers = []
                link = (e.registration.url if e.registration and e.registration.url else None) or e.url
                if link:
                    offers.append(
                        {
                            "seller": e.organizer or ctx.source.name,
                            "kind": "registration" if e.registration else "info",
                            "url": link,
                            "price_min": e.price_min,
                            "price_max": e.price_max,
                            "availability": avail,
                            "source_id": ctx.source.id,
                            "fetched_at": fetched_at,
                        }
                    )
                yield ctx.base(
                    f"{e.id}:{start.date().isoformat()}" if e.weekly else e.id,
                    title=e.title,
                    description=clean_text(desc, 4000),
                    url=e.url or e.source_url,
                    kind=e.kind if not e.weekly else EventKind.RECURRING,
                    category=e.category,
                    tags=e.tags,
                    start=start,
                    end=end,
                    all_day=all_day,
                    recurrence=e.recurrence,
                    location={
                        "venue_name": e.venue,
                        "address": e.address,
                        "lat": e.lat,
                        "lon": e.lon,
                        "geocode_method": "curated" if e.lat is not None else None,
                    },
                    organizer=e.organizer,
                    price={"is_free": True}
                    if e.free
                    else {"min": e.price_min, "max": e.price_max, "note": e.price_note},
                    offers=offers,
                    registration=reg,
                    availability=avail,
                    fetched_at=fetched_at,
                    extras={
                        "curated_verified_at": e.verified_at.isoformat(),
                        "page_watch": page_state,
                        "evidence_url": str(e.source_url),
                    },
                )


def _entries(content: bytes) -> list[CuratedEntry]:
    data = yaml.safe_load(content) or []
    return [CuratedEntry.model_validate(x) for x in data]


def _dt(v: date | datetime | None, tz: ZoneInfo, default: time) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=tz)
    return datetime.combine(v, default, tz)


def _starts(e: CuratedEntry, local_now: datetime, tz: ZoneInfo) -> list[tuple[datetime, datetime | None, bool]]:
    if e.weekly:
        hh, mm = (int(x) for x in e.weekly.at.split(":"))
        out: list[tuple[datetime, datetime | None, bool]] = []
        first = max(
            local_now.date(), e.start.date() if isinstance(e.start, datetime) else (e.start or local_now.date())
        )
        d = first
        last = e.end.date() if isinstance(e.end, datetime) else e.end
        while len(out) < e.weekly.occurrences and (d - first).days < 60:
            if d.weekday() in {_DAYS[x] for x in e.weekly.days} and (last is None or d <= last):
                s = datetime.combine(d, time(hh, mm), tz)
                if s >= local_now - timedelta(hours=1):
                    out.append((s, s + timedelta(minutes=e.weekly.duration_min), False))
            d += timedelta(days=1)
        return out
    if e.start is None:
        return []
    all_day = not isinstance(e.start, datetime) and e.at is None
    if isinstance(e.start, datetime):
        start = e.start if e.start.tzinfo else e.start.replace(tzinfo=tz)
    else:
        hh, mm = (int(x) for x in e.at.split(":")) if e.at else (0, 0)
        t = time(hh, mm)
        start = datetime.combine(e.start, t, tz)
    end = _dt(e.end, tz, time(23, 59)) if e.end else None
    return [(start, end, all_day)]
