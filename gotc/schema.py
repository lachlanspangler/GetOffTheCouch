"""The GetOffTheCouch event schema — the single contract between every layer.

Layers:
  adapters  → produce ``SourceEvent`` (one source's view of one event, already normalized)
  pipeline  → resolves ``SourceEvent``s into canonical ``Event``s (dedup, geocode, enrich)
  export    → serializes ``Event``s into ``CityFeed`` JSON for the dashboard

Rules baked into the types:
  * every datetime is timezone-aware (naive datetimes are rejected)
  * categories are taxonomy ids (validated against config/taxonomy.yaml at the pipeline boundary)
  * every estimate carries a method and a low/high band — never a bare number
  * demo/seed data is flagged with ``is_demo`` and never mixed into real exports

Bump ``SCHEMA_VERSION`` (semver) whenever an exported field changes. Minor = additive, major = breaking.
The dashboard's TypeScript types are generated from ``CityFeed.model_json_schema()`` (``make schema``).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, HttpUrl, model_validator

SCHEMA_VERSION = "1.7.0"


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("datetime must be timezone-aware")
    return dt


AwareDatetime = Annotated[datetime, AfterValidator(_aware)]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
Money = Annotated[float, Field(ge=0.0)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False, str_strip_whitespace=True)


# ───────────────────────────── enums ─────────────────────────────


class DataType(StrEnum):
    """What kind of data a source provides. Drives the freshness SLA (config/sources.yaml)."""

    TICKET_PRICES = "ticket_prices"
    CONCERTS = "concerts"
    EVENTS = "events"
    LEAGUES = "leagues"
    VOLUNTEER = "volunteer"
    OPENINGS = "openings"
    CONVENTIONS = "conventions"
    RECURRING = "recurring"


class EventKind(StrEnum):
    ONE_OFF = "one_off"  # a dated happening
    RECURRING = "recurring"  # trivia every Tuesday, run club every Saturday
    SEASON = "season"  # a league season: registration window + season dates
    OPENING = "opening"  # a new bar/restaurant/venue opening (may only have an approximate date)
    DEADLINE = "deadline"  # a pure deadline (e.g. "lottery applications close")


class Availability(StrEnum):
    ON_SALE = "on_sale"
    LIMITED = "limited"
    FEW_LEFT = "few_left"
    SOLD_OUT = "sold_out"
    NOT_YET_ON_SALE = "not_yet_on_sale"
    REGISTRATION_OPEN = "registration_open"
    REGISTRATION_CLOSED = "registration_closed"
    WAITLIST = "waitlist"
    FREE_NO_TICKET = "free_no_ticket"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"
    UNKNOWN = "unknown"


class OfferKind(StrEnum):
    PRIMARY = "primary"  # face value from the official seller
    RESALE = "resale"  # secondary market
    REGISTRATION = "registration"  # league / race / class signup
    RSVP = "rsvp"  # free, but RSVP
    INFO = "info"  # informational page, no transaction


class Method(StrEnum):
    """How a value was obtained. Shown in the UI next to every non-reported value."""

    REPORTED = "reported"  # the source said so
    DERIVED = "derived"  # deterministic transform of reported data (e.g. tz conversion, geocode)
    EXTRACTED = "extracted"  # pulled out of free text (e.g. "register by Oct 3")
    ESTIMATED = "estimated"  # a model — always comes with a band
    CURATED = "curated"  # a human/agent verified it by hand (with a source URL)


class SignupType(StrEnum):
    TEAM = "team"
    FREE_AGENT = "free_agent"
    INDIVIDUAL = "individual"
    GROUP = "group"


class SkillLevel(StrEnum):
    BEGINNER = "beginner"
    RECREATIONAL = "recreational"
    INTERMEDIATE = "intermediate"
    COMPETITIVE = "competitive"
    ALL = "all"


# ───────────────────────────── building blocks ─────────────────────────────


class FieldProvenance(Strict):
    source: str
    fetched_at: AwareDatetime
    method: Method = Method.REPORTED
    confidence: Confidence = 1.0
    note: str | None = None


class SourceRef(Strict):
    """One source's record of an event. A canonical event keeps all of them."""

    source_id: str
    record_id: str
    url: HttpUrl | None = None
    fetched_at: AwareDatetime
    first_seen: AwareDatetime | None = None


class Location(Strict):
    venue_name: str | None = None
    address: str | None = None
    neighborhood: str | None = None
    lat: Annotated[float, Field(ge=-90, le=90)] | None = None
    lon: Annotated[float, Field(ge=-180, le=180)] | None = None
    geocode_method: Method | None = None
    geocode_confidence: Confidence | None = None

    @model_validator(mode="after")
    def _both_or_neither(self) -> Location:
        if (self.lat is None) != (self.lon is None):
            raise ValueError("lat and lon must both be set or both be empty")
        return self


class Price(Strict):
    """Price summary in USD. ``is_free`` is only true when a source said so."""

    min: Money | None = None
    max: Money | None = None
    currency: Literal["USD"] = "USD"
    is_free: bool = False
    note: str | None = None  # e.g. "suggested donation", "+ fees", "per team"

    @model_validator(mode="after")
    def _ordered(self) -> Price:
        if self.min is not None and self.max is not None and self.min > self.max:
            self.min, self.max = self.max, self.min
        if self.is_free and (self.min or self.max):
            raise ValueError("free event cannot have a non-zero price")
        return self


class Offer(Strict):
    """A way to get in: a ticket listing, a registration page, an RSVP."""

    seller: str  # "Ticketmaster", "SeatGeek", "Volo", "City of Minneapolis"
    kind: OfferKind
    url: HttpUrl
    price_min: Money | None = None
    price_max: Money | None = None
    listing_count: Annotated[int, Field(ge=0)] | None = None
    availability: Availability = Availability.UNKNOWN
    fees_included: bool | None = None
    affiliate: bool = False
    source_id: str
    fetched_at: AwareDatetime


class Registration(Strict):
    """Deadlines. ``closes_at`` is the headline 'register by' date."""

    opens_at: AwareDatetime | None = None
    closes_at: AwareDatetime | None = None
    early_bird_ends_at: AwareDatetime | None = None
    signup_types: list[SignupType] = Field(default_factory=list)
    skill_levels: list[SkillLevel] = Field(default_factory=list)
    url: HttpUrl | None = None
    evidence: str | None = None  # the text the date was extracted from
    method: Method = Method.REPORTED
    confidence: Confidence = 1.0


class Estimate(Strict):
    """A modeled number. Always a band; ``mid`` is the point estimate shown with a '~'."""

    low: Annotated[float, Field(ge=0)]
    mid: Annotated[float, Field(ge=0)]
    high: Annotated[float, Field(ge=0)]
    method: str  # human-readable: "venue capacity 1,800 × 85% fill (sold-out signal)"
    inputs: dict[str, str | float | int | bool | None] = Field(default_factory=dict)
    confidence: Confidence

    @model_validator(mode="after")
    def _band(self) -> Estimate:
        if not (self.low <= self.mid <= self.high):
            raise ValueError("estimate must satisfy low <= mid <= high")
        return self


class TicketSignal(Strict):
    availability: Availability = Availability.UNKNOWN
    spots_left: Annotated[int, Field(ge=0)] | None = None  # reported by the source (volunteer shifts, classes)
    spots_total: Annotated[int, Field(gt=0)] | None = None
    pct_left: Estimate | None = None  # 0–100
    selling_fast: bool = False
    signal: str | None = None  # "listings down 38% in 48h", "few tickets left flag"


class PricePoint(Strict):
    at: AwareDatetime
    seller: str
    price_min: Money | None = None
    price_max: Money | None = None
    listing_count: Annotated[int, Field(ge=0)] | None = None


class PriceTrend(Strict):
    direction: Literal["up", "down", "flat", "unknown"] = "unknown"
    change_pct: float | None = None  # lowest price change over the window
    window_hours: int | None = None
    points: list[PricePoint] = Field(default_factory=list)


class Weather(Strict):
    """NWS hourly forecast for the event's start hour (outdoor events, ≤ ~6 days out)."""

    short: str
    temp_f: float | None = None
    precip_pct: Annotated[float, Field(ge=0, le=100)] | None = None
    source: Literal["nws"] = "nws"
    fetched_at: AwareDatetime


class SocialScore(Strict):
    """How good an event is for meeting people (0–1), with reasons the UI shows."""

    score: Confidence
    reasons: list[str] = Field(default_factory=list)


class RankHints(Strict):
    """Profile-independent ranking hints precomputed at export (gotc/pipeline/rankprep.py, RANKING.md §5.1).

    Short keys keep the card feed lean. Every value is derived from the event's own fields or run history.
    """

    fp: str = Field(description="near-duplicate fingerprint: equal fp = same listing (title|venue|local date)")
    group: str | None = Field(default=None, description="multi-site group id: same program, same day, 2+ venues")
    group_n: Annotated[int, Field(ge=1)] = Field(default=1, description="venues in the multi-site group")
    desc_len: Annotated[int, Field(ge=0)] = Field(default=0, description="full description length in chars")
    flags: list[str] = Field(default_factory=list, description="quality flags (admin, no_info, no_place, ...)")
    lowq: Confidence = Field(default=0.0, description="low-quality score: sum of flag weights, capped at 1")
    complete: Confidence = Field(default=0.0, description="completeness: share of 7 key fields present")
    quality: Confidence = Field(default=0.0, description="complete × (1 − lowq)")
    src_rel: Confidence | None = Field(default=None, description="best source unit's 30-day reliability, 0–1")


# ───────────────────────────── adapter output ─────────────────────────────


class SourceEvent(Strict):
    """One source's normalized view of one event. Produced by adapters, validated at the boundary."""

    source_id: str
    record_id: str  # stable id within the source
    city: str
    title: Annotated[str, Field(min_length=2, max_length=300)]
    description: str | None = None
    url: HttpUrl | None = None
    kind: EventKind = EventKind.ONE_OFF
    category: str  # taxonomy id
    source_categories: list[str] = Field(default_factory=list)  # raw labels, kept for re-mapping
    tags: list[str] = Field(default_factory=list)
    start: AwareDatetime
    end: AwareDatetime | None = None
    all_day: bool = False
    timezone: str
    recurrence: str | None = None  # human-readable ("Tuesdays 7pm")
    location: Location = Field(default_factory=Location)
    organizer: str | None = None
    price: Price = Field(default_factory=Price)
    offers: list[Offer] = Field(default_factory=list)
    registration: Registration | None = None
    availability: Availability = Availability.UNKNOWN
    venue_capacity: Annotated[int, Field(gt=0)] | None = None
    reported_attendance: Annotated[int, Field(gt=0)] | None = None
    fetched_at: AwareDatetime
    is_demo: bool = False
    extras: dict[str, str | float | int | bool | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _ordering(self) -> SourceEvent:
        if self.end is not None and self.end < self.start:
            raise ValueError("end before start")
        return self


# ───────────────────────────── canonical / exported ─────────────────────────────


class Venue(Strict):
    id: str
    name: str
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    neighborhood: str | None = None
    capacity: int | None = None
    capacity_source: str | None = None
    url: HttpUrl | None = None


class Event(Strict):
    """A canonical, deduplicated, enriched event — what the dashboard renders."""

    id: str
    city: str
    title: str
    summary: str | None = None
    url: HttpUrl | None = None
    kind: EventKind
    category: str
    categories: list[str] = Field(default_factory=list)  # category + secondary categories
    tags: list[str] = Field(default_factory=list)
    start: AwareDatetime
    end: AwareDatetime | None = None
    all_day: bool = False
    timezone: str
    recurrence: str | None = None
    series_id: str | None = None  # occurrences of one repeating thing share this (UI shows one card)
    series_dates: list[AwareDatetime] = Field(default_factory=list)  # upcoming starts in the series (≤8)
    location: Location
    venue_id: str | None = None
    organizer: str | None = None
    price: Price
    offers: list[Offer] = Field(default_factory=list)
    registration: Registration | None = None
    attendance: Estimate | None = None
    tickets: TicketSignal = Field(default_factory=TicketSignal)
    price_trend: PriceTrend | None = None
    social: SocialScore | None = None
    weather: Weather | None = None
    sources: list[SourceRef]
    provenance: dict[str, FieldProvenance] = Field(default_factory=dict)
    first_seen: AwareDatetime
    last_checked: AwareDatetime
    is_new: bool = False  # first listed in the last 72h (and not part of a source's initial backfill)
    stale: bool = False
    stale_reason: str | None = None
    is_demo: bool = False
    rank: RankHints | None = None  # precomputed ranking hints (schema 1.5.0)


class SourceStatus(Strict):
    source_id: str
    name: str
    state: Literal["healthy", "degraded", "quarantined", "recovering", "disabled", "never_run"]
    last_success_at: AwareDatetime | None = None
    last_attempt_at: AwareDatetime | None = None
    sla_hours: float
    stale: bool
    records: int
    last_error: str | None = None
    reason: str | None = None  # e.g. "needs TICKETMASTER_API_KEY"


class StarterItem(Strict):
    """An official new-resident deadline/to-do (e.g. "license within 60 days"), quoted from a .gov page."""

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str
    kind: Literal["license", "vehicle", "voting", "id", "inspection", "other"]
    days_after_move: Annotated[int, Field(ge=0, le=730)] | None = None
    summary: str
    action_url: HttpUrl
    evidence: str = Field(min_length=12)
    source_url: HttpUrl
    verified_at: date
    check_status: Literal["evidence_present", "page_changed", "unchecked"] = "unchecked"
    last_checked: AwareDatetime | None = None


class NeighborhoodPoint(Strict):
    name: str
    lat: float
    lon: float


class CoverageCriterion(Strict):
    """One go-live gate criterion (docs/research/SCALING.md §3, ADR-0008). ``None`` = not part of that bar."""

    label: str
    value: float | None = None  # the measured number (counts, or shares 0–1)
    threshold: str  # human-readable, e.g. "≥ 250 (hard)"
    pass_hard: bool | None = None
    pass_soft: bool | None = None
    note: str | None = None


class CoveragePillar(Strict):
    """A newcomer pillar's coverage: ✓ strong, ◐ thin, ✕ none."""

    label: str
    count: Annotated[int, Field(ge=0)]
    threshold: Annotated[int, Field(ge=1)]  # count at which the pillar is "strong"
    state: Literal["strong", "thin", "none"]
    note: str | None = None  # e.g. "all curated", "we have no license data for this city"


class CityCoverage(Strict):
    """Per-city coverage + go-live tier, computed by ``gotc gate``. The UI never computes coverage itself."""

    tier: Literal["live", "beta", "hidden"]
    evaluated_at: AwareDatetime
    passed_hard: bool
    passed_soft: bool
    failing_since: AwareDatetime | None = None  # a live city failing a hard criterion since …
    banner: bool = False  # live city failing a hard criterion for > 72 h: show a banner
    sources_healthy: Annotated[int, Field(ge=0)]
    sources_total: Annotated[int, Field(ge=0)]
    pillars: dict[str, CoveragePillar] = Field(default_factory=dict)
    strongest: list[str] = Field(default_factory=list)  # pillar ids, strongest first
    geocode_rate: Confidence  # share of exported events with coordinates
    top_source: str | None = None
    top_source_share: Confidence = 0.0
    criteria: dict[str, CoverageCriterion] = Field(default_factory=dict)  # G1…G11
    reasons: list[str] = Field(default_factory=list)  # why the city isn't fully live / soft notes


class CityFeed(Strict):
    """The exported per-city document: ``web/public/data/cities/<slug>.json``."""

    schema_version: str = SCHEMA_VERSION
    generated_at: AwareDatetime
    city: str
    city_name: str
    state: str
    timezone: str
    center: tuple[float, float]
    neighborhoods: list[NeighborhoodPoint] = Field(default_factory=list)  # approximate centroids
    events: list[Event]
    venues: list[Venue] = Field(default_factory=list)
    sources: list[SourceStatus] = Field(default_factory=list)
    starter_pack: list[StarterItem] = Field(default_factory=list)  # state new-resident deadlines
    coverage: CityCoverage | None = None  # go-live tier + coverage block (1.5.0); also in index.json
    is_demo: bool = False


class EventDetail(Strict):
    """Heavy per-event fields, moved out of the card feed and loaded when a card is opened."""

    summary: str | None = None
    provenance: dict[str, FieldProvenance] = Field(default_factory=dict)


class CityDetails(Strict):
    """``web/public/data/cities/<slug>.details.json``: EventDetail by event id."""

    schema_version: str = SCHEMA_VERSION
    generated_at: AwareDatetime
    city: str
    events: dict[str, EventDetail]


# --- week-sharded city data (1.7.0, I-117) ------------------------------------------------------------------------
# The legacy ``cities/<slug>.json`` + ``.details.json`` stay as they are. Next to them, ``cities/<slug>/`` holds the
# same cards split by the week an event starts (in the city's timezone), so a visitor downloads the next two weeks
# first and the rest in idle time. Shard file names carry a content hash, so Pages' 10-minute cache can never serve
# a stale shard after a deploy; only ``manifest.json`` is unhashed and is always revalidated (``no-cache``).

ShardKind = Literal["ongoing", "deadlines", "week", "openings", "later", "past"]


class ShardFile(Strict):
    file: str  # path relative to ``cities/<slug>/``, e.g. ``w/2026-W44.3f9a1c2b7d.json``
    sha256: str  # hex digest of the file's bytes (the name carries its first 10 characters)
    bytes: int = Field(ge=0)


class ShardRef(Strict):
    """One card shard and its matching details shard."""

    key: str  # "ongoing" | "deadlines" | "openings" | "later" | ISO week "2026-W44" | "past-2026-W42"; ".2"… = parts
    kind: ShardKind
    starts: date | None = None  # week and past shards: the Monday the ISO week starts (city time)
    ends: date | None = None  # week shards: the following Monday (exclusive)
    events: int = Field(ge=0)
    cards: ShardFile  # CityShard
    details: ShardFile  # CityShardDetails


class CityManifest(Strict):
    """``web/public/data/cities/<slug>/manifest.json``: which shard files make up the city's feed right now.

    Every card event of ``cities/<slug>.json`` is in exactly one shard, listed in this load order:
      * ``ongoing``: started before the export's current week and still running (exhibits, multi-week faires)
      * ``deadlines``: starts after next week but has a registration date the deadline views need now
      * ``week``: starts in that ISO week, for the current week and the next ``SHARD_WEEKS`` weeks
      * ``openings``: license signals (``kind: opening``); their start is a filing date, not a date to go
      * ``later``: everything further out (league seasons and cons planned months ahead)
      * ``past``: started in an earlier week (key ``past-<week>``) and already over; for saved items and ended pages
    ``meta`` is the CityFeed with ``events: []`` (city, venues, sources, starter pack, coverage).
    """

    schema_version: str = SCHEMA_VERSION
    generated_at: AwareDatetime
    city: str
    timezone: str
    current_week: str  # ISO week of ``generated_at`` in the city's timezone
    meta: ShardFile
    shards: list[ShardRef]
    legacy: str  # the monolithic card file, relative to this manifest (``../<slug>.json``)


class CityShard(Strict):
    """``cities/<slug>/w/<key>.<hash>.json``: the cards of one shard, in feed order."""

    schema_version: str = SCHEMA_VERSION
    city: str
    key: str
    events: list[Event]


class CityShardDetails(Strict):
    """``cities/<slug>/d/<key>.<hash>.json``: EventDetail by event id for one shard."""

    schema_version: str = SCHEMA_VERSION
    city: str
    key: str
    events: dict[str, EventDetail]
