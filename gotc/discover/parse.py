"""Pure parsers for discovery probes. No network here; every function is tested from recorded fixtures
(tests/fixtures/discover/). Shapes were verified live on 2026-10-16 (docs/research/SCALING.md §2).
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlsplit

US_TLDS = {"gov", "us", "org", "com", "net", "edu", "io", "info", "mil"}
SANDBOX = re.compile(r"(^|\.)(demo|sandbox|test|integration-[^.]*|staging)[.-]|socrata\.com$", re.I)

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}  # fmt: skip


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def mentions(text: str, terms: list[str]) -> bool:
    low = f" {re.sub(r'[^a-z0-9]+', ' ', text.lower())} "
    return any(f" {re.sub(r'[^a-z0-9]+', ' ', t.lower()).strip()} " in low for t in terms if t.strip())


def us_host(host: str) -> bool:
    host = host.lower().split(":")[0]
    return host.rsplit(".", 1)[-1] in US_TLDS and not SANDBOX.search(host)


# ── government open data ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Dataset:
    platform: str  # socrata | arcgis | datagov
    domain: str
    id: str
    name: str
    updated_at: str | None = None
    columns: list[str] = field(default_factory=list)
    column_types: list[str] = field(default_factory=list)
    publisher: str | None = None
    url: str | None = None
    views_last_month: int | None = None


def socrata_catalog(data: dict[str, Any], place_terms: list[str], state: str) -> list[Dataset]:
    """Socrata Discovery API results kept when the tenant, attribution or name names the place or the state.

    State-portal datasets (``data.texas.gov``) count: license data is often statewide (filtered later by city).
    Non-US tenants and sandbox/demo tenants are dropped.
    """
    out: list[Dataset] = []
    state_terms = [STATE_NAMES.get(state, state)]
    for r in data.get("results") or []:
        res, meta = r.get("resource") or {}, r.get("metadata") or {}
        domain = str(meta.get("domain") or "")
        if not domain or not us_host(domain) or res.get("type") not in (None, "dataset"):
            continue
        hay = " ".join(str(x or "") for x in (domain.replace(".", " "), res.get("attribution"), res.get("name")))
        state_portal = mentions(domain.replace(".", " "), [state_terms[0], state.lower()]) and domain.startswith(
            ("data.", "opendata.")
        )
        if not (mentions(hay, place_terms) or state_portal or mentions(hay, state_terms)):
            continue
        out.append(
            Dataset(
                "socrata",
                domain,
                str(res.get("id") or ""),
                str(res.get("name") or ""),
                updated_at=res.get("data_updated_at") or res.get("updatedAt"),
                columns=list(res.get("columns_field_name") or []),
                column_types=list(res.get("columns_datatype") or []),
                publisher=res.get("attribution"),
                url=r.get("permalink") or r.get("link"),
                views_last_month=(res.get("page_views") or {}).get("page_views_last_month"),
            )
        )
    return [d for d in out if d.id]


SOCRATA_VIEW = re.compile(r"https?://([a-z0-9.-]+)/api/views/([a-z0-9]{4}-[a-z0-9]{4})", re.I)
LOCAL_ORGS = {"City Government", "County Government", "State Government", "Local Government"}


def datagov_search(data: dict[str, Any], place_terms: list[str]) -> list[Dataset]:
    """catalog.data.gov ``/search`` (the post-CKAN API): local/state government datasets naming the place.

    A Socrata ``/api/views/<id>`` identifier tells us the platform and dataset id directly.
    """
    out: list[Dataset] = []
    for r in data.get("results") or []:
        org = r.get("organization") or {}
        title = str(r.get("title") or "")
        hay = " ".join(str(x or "") for x in (title, r.get("publisher"), org.get("name")))
        if org.get("organization_type") not in LOCAL_ORGS or not mentions(hay, place_terms):
            continue
        ident = str(r.get("identifier") or "")
        m = SOCRATA_VIEW.match(ident)
        dcat = r.get("dcat") or {}
        if m:
            out.append(
                Dataset("socrata", m.group(1), m.group(2), title, dcat.get("modified"), publisher=r.get("publisher"))
            )
        else:
            out.append(
                Dataset(
                    "datagov",
                    "catalog.data.gov",
                    str(r.get("slug") or ident),
                    title,
                    dcat.get("modified"),
                    publisher=r.get("publisher"),
                    url=f"https://catalog.data.gov/dataset/{r.get('slug')}" if r.get("slug") else ident or None,
                )
            )
    return out


@dataclass
class HubSite:
    title: str
    source: str
    org_id: str
    url: str
    owner: str


def hub_sites(data: dict[str, Any], place_terms: list[str]) -> list[HubSite]:
    """ArcGIS Hub OGC Records site search → official sites whose title/source/owner/url names the place."""
    out = []
    for f in data.get("features") or []:
        p = f.get("properties") or {}
        site = HubSite(
            str(p.get("title") or "").strip(),
            str(p.get("source") or ""),
            str(p.get("orgId") or ""),
            str(p.get("url") or ""),
            str(p.get("owner") or ""),
        )
        hay = " ".join(
            [site.title, site.source, site.owner.replace("_", " "), urlsplit(site.url).netloc.replace("-", " ")]
        )
        if site.org_id and mentions(hay, place_terms) and not SANDBOX.search(urlsplit(site.url).netloc):
            out.append(site)
    return out


def arcgis_search(data: dict[str, Any]) -> list[Dataset]:
    """www.arcgis.com sharing/rest/search (org-scoped) → public Feature Services."""
    out = []
    for r in data.get("results") or []:
        if r.get("access") not in (None, "public") or not r.get("url"):
            continue
        mod = r.get("modified")
        updated = datetime.fromtimestamp(mod / 1000, tz=UTC).isoformat() if isinstance(mod, int | float) else None
        out.append(
            Dataset(
                "arcgis",
                urlsplit(str(r["url"])).netloc,
                str(r.get("id") or ""),
                str(r.get("title") or ""),
                updated,
                publisher=r.get("owner"),
                url=str(r["url"]),
                views_last_month=r.get("numViews"),
            )
        )
    return out


START_COLS = ("original_issue_date", "license_start_date", "application_date", "submission_date", "issue_date",
              "start_date", "event_date", "date", "start")  # fmt: skip
TITLE_COLS = ("dba_name", "doing_business_as_name", "trade_name", "business_name", "event_name", "name", "title")
REFUSE_DATE = re.compile(r"renew|expir", re.I)


def guess_socrata_fields(columns: list[str]) -> dict[str, str]:
    """A starting field mapping for a candidate Socrata unit (a human reviews it before promotion).

    Never maps renewal/expiration columns as the start (ADR-0006).
    """
    cols = [c for c in columns if not c.startswith(":")]
    fields: dict[str, str] = {}
    for want in START_COLS:
        hit = next((c for c in cols if (c == want or c.endswith("_" + want)) and not REFUSE_DATE.search(c)), None)
        if hit:
            fields["start"] = hit
            break
    for want in TITLE_COLS:
        hit = next((c for c in cols if c == want or c.endswith("_" + want)), None)
        if hit:
            fields["title"] = hit
            break
    for want, keys in (("lat", ("latitude", "lat")), ("lon", ("longitude", "lon", "long"))):
        hit = next((c for c in cols if c in keys), None)
        if hit:
            fields[want] = hit
    if "lat" not in fields:
        loc = next((c for c in cols if c in ("location", "geocoded_column", "the_geom", "point")), None)
        if loc:
            fields["point"] = loc
    addr = next((c for c in cols if c in ("address", "street_address", "location_address", "full_address")), None)
    if addr:
        fields["address"] = addr
    return fields


# ── platform fingerprints (homepages, /events, /calendar) ────────────────────────────────────────────

_BC = re.compile(r"\b([a-z0-9]+)\.bibliocommons\.com", re.I)
_BC_NOT = {"gateway", "www", "cdn", "static", "assets", "secure", "help", "support", "api"}
_LIBNET = re.compile(r"\b([a-z0-9-]+)\.libnet\.info", re.I)
_LIBCAL = re.compile(r"\b([a-z0-9-]+\.libcal\.com)", re.I)
_LIBCAL_CID = re.compile(r"(?:baseCalendarId:\s*|cal_id=\"?)(\d+)")
_TRUMBA = re.compile(r"""webName\s*:\s*["']([A-Za-z0-9_.-]+)["']""")
_LIBCAL_LINK = re.compile(r"https?://([a-z0-9.-]+)/calendar[^\"' ]*\?cid=-?\d+&(?:amp;)?t=", re.I)
_EVENT_HOST = re.compile(r"https?://((?:events?|calendars?)\.[a-z0-9-]+(?:\.[a-z0-9-]+)+)", re.I)
_GALAXY = re.compile(r"\b([a-z0-9-]+)\.galaxydigital\.com", re.I)
_HOC_BLOCK = re.compile(r"calendar-search-block-id[^0-9]{0,40}(\d+)", re.I)
_LD = re.compile(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", re.S | re.I)
_SITE_NAME = re.compile(r"""<meta[^>]+property=["']og:site_name["'][^>]+content=["']([^"']+)""", re.I)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


@dataclass
class Fingerprint:
    platforms: dict[str, list[str]] = field(default_factory=dict)  # platform → keys (codes, hosts, ids)
    jsonld_events: int = 0
    site_name: str | None = None
    title: str | None = None
    cloudflare: bool = False
    wordpress: bool = False

    def add(self, platform: str, key: str) -> None:
        keys = self.platforms.setdefault(platform, [])
        if key not in keys:
            keys.append(key)


def is_cloudflare_challenge(text: str, status: int | None = None) -> bool:
    t = text[:20000]
    return (
        "Just a moment..." in t
        or "cf-browser-verification" in t
        or "challenge-platform" in t
        or ("Attention Required!" in t and "Cloudflare" in t)
        or (status in (403, 503) and "cloudflare" in t.lower())
    )


def fingerprint(html: str, base_url: str) -> Fingerprint:
    fp = Fingerprint()
    if is_cloudflare_challenge(html):
        fp.cloudflare = True
        return fp
    if m := _SITE_NAME.search(html):
        fp.site_name = m.group(1).strip()
    if m := _TITLE.search(html):
        fp.title = re.sub(r"\s+", " ", m.group(1)).strip()[:200]
    for code in _BC.findall(html):
        if code.lower() not in _BC_NOT:
            fp.add("bibliocommons", code.lower())
    for sub in _LIBNET.findall(html):
        fp.add("communico", f"https://{sub.lower()}.libnet.info")
    if "eeventcaldata" in html:
        fp.add("communico", base_url.rstrip("/"))
    for host in _LIBCAL.findall(html):
        if not host.lower().startswith("static-assets"):
            fp.add("libcal", f"https://{host.lower()}")
    for host in _LIBCAL_LINK.findall(html):  # LibCal on a custom domain (calendar.<library>.org)
        fp.add("libcal", f"https://{host.lower()}")
    if "static-assets-us.libcal.com" in html or "springshare" in html.lower():
        fp.add("libcal", base_url.rstrip("/"))
    own = urlsplit(base_url).netloc.lower()
    for host in _EVENT_HOST.findall(html):
        if host.lower() != own and not host.lower().endswith((".libcal.com", ".bibliocommons.com", ".libnet.info")):
            fp.add("event_host", f"https://{host.lower()}")
    for cid in _LIBCAL_CID.findall(html):
        fp.add("libcal_cid", cid)
    if "trumba.com/scripts/spuds.js" in html or "$Trumba" in html:
        for name in _TRUMBA.findall(html):
            fp.add("trumba", name)
    for sub in _GALAXY.findall(html):
        if sub.lower() not in ("www", "api", "cdn", "help"):
            fp.add("galaxydigital", f"https://{sub.lower()}.galaxydigital.com")
    if "handsonconnect" in html.lower():
        m = _HOC_BLOCK.search(html)
        fp.add("handsonconnect", m.group(1) if m else "")
    if "localist" in html.lower() and "/api/2/" in html:
        fp.add("localist", base_url)
    if "/live/json/" in html or "livewhale" in html.lower():
        fp.add("livewhale", base_url)
    if "tribe-events" in html or "tribe/events/v1" in html:
        fp.add("tribe", base_url)
    if "RSSFeed.aspx" in html or "CivicPlus" in html:
        fp.add("civicplus", base_url)
    for host in re.findall(r"https?://([a-z0-9.-]*(?:activecommunities\.com|recdesk\.com|rec1\.com))", html, re.I):
        fp.add("registration_platform", host.lower())
    fp.wordpress = "wp-content/" in html or "api.w.org" in html
    fp.jsonld_events = jsonld_event_count(html)
    return fp


def _walk_types(node: Any) -> list[str]:
    out: list[str] = []
    if isinstance(node, list):
        for n in node:
            out += _walk_types(n)
    elif isinstance(node, dict):
        t = node.get("@type")
        for x in t if isinstance(t, list) else [t]:
            if isinstance(x, str):
                out.append(x)
        for k in ("@graph", "itemListElement", "subEvent", "item", "event", "events"):
            if k in node:
                out += _walk_types(node[k])
    return out


def jsonld_event_count(html: str) -> int:
    n = 0
    for block in _LD.findall(html):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        n += sum(1 for t in _walk_types(data) if t.endswith("Event"))
    return n


# ── endpoint probes ──────────────────────────────────────────────────────────────────────────────────


@dataclass
class FeedProbe:
    ok: bool
    items: int = 0
    title: str | None = None
    sample: list[str] = field(default_factory=list)
    places: list[str] = field(default_factory=list)  # locality/branch strings, for geo fit
    note: str | None = None


_ITEM = re.compile(r"<item\b.*?</item>", re.S | re.I)
_ITEM_TITLE = re.compile(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", re.S | re.I)


def rss(xml: str) -> FeedProbe:
    items = _ITEM.findall(xml)
    head = xml.split("<item", 1)[0]
    m = _ITEM_TITLE.search(head)
    titles = [re.sub(r"\s+", " ", t.group(1)).strip() for t in (_ITEM_TITLE.search(i) for i in items[:5]) if t]
    ok = "<rss" in xml[:2000] or "<channel" in xml[:4000]
    return FeedProbe(ok, len(items), m.group(1).strip() if m else None, titles)


def bibliocommons_rss(xml: str) -> FeedProbe:
    """gateway.bibliocommons.com/v2/libraries/<code>/rss/events: 200 + items = events on BiblioCommons;
    200 + empty channel = the code exists but events live elsewhere (the channel title still confirms it)."""
    p = rss(xml)
    p.places = re.findall(r"<bc:location>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</bc:location>", xml)[:20]
    if p.ok and not p.items:
        p.note = "code exists; events not on BiblioCommons"
    return p


def galaxy_rss(xml: str) -> FeedProbe:
    """<tenant>.galaxydigital.com/need/rss/: unknown tenants answer 200 with "Galaxy Digital: Bad Domain"."""
    p = rss(xml)
    if "Bad Domain" in xml[:3000]:
        return FeedProbe(False, note="Galaxy Digital: Bad Domain (no such tenant)")
    return p


def carbonhouse_rss(xml: str) -> FeedProbe:
    p = rss(xml)
    if p.ok and "xmlns:ev" not in xml[:3000]:
        p.note = "RSS without the ev: namespace (not a carbonhouse event feed)"
    return p


def wp_has_tribe(data: Any) -> bool:
    return isinstance(data, dict) and "tribe/events/v1" in (data.get("namespaces") or [])


def tribe_events(data: Any) -> FeedProbe:
    if not isinstance(data, dict) or "events" not in data:
        return FeedProbe(False, note="not a Tribe events response")
    evs = data.get("events") or []
    places = [str((e.get("venue") or {}).get("city") or "") for e in evs if isinstance(e.get("venue"), dict)]
    return FeedProbe(
        True, int(data.get("total") or len(evs)), None, [str(e.get("title", ""))[:80] for e in evs[:5]], places
    )


def localist_events(data: Any) -> FeedProbe:
    if not isinstance(data, dict) or "events" not in data:
        return FeedProbe(False, note="not a Localist response")
    page = data.get("page") or {}
    evs = [e.get("event") or {} for e in data.get("events") or []]
    return FeedProbe(
        True,
        int(page.get("total_items") or len(evs)),
        None,
        [str(e.get("title", ""))[:80] for e in evs[:5]],
        [str((e.get("geo") or {}).get("city") or "") for e in evs],
    )


def livewhale_events(data: Any) -> FeedProbe:
    if not isinstance(data, list):
        return FeedProbe(False, note="not a LiveWhale JSON array")
    return FeedProbe(True, len(data), None, [str(e.get("title", ""))[:80] for e in data[:5] if isinstance(e, dict)])


def trumba_events(data: Any) -> FeedProbe:
    if not isinstance(data, list):
        return FeedProbe(False, note="not a Trumba JSON array")
    return FeedProbe(
        True,
        len(data),
        None,
        [str(e.get("title", ""))[:80] for e in data[:5] if isinstance(e, dict)],
        [str(e.get("location", ""))[:80] for e in data if isinstance(e, dict)],
    )


def communico_events(data: Any) -> FeedProbe:
    if not isinstance(data, list):
        return FeedProbe(False, note="not a Communico eeventcaldata array")
    libs = sorted({str(e.get("library", "")) for e in data if isinstance(e, dict) and e.get("library")})
    deadlines = sum(1 for e in data if isinstance(e, dict) and e.get("close_registration"))
    return FeedProbe(
        True,
        len(data),
        None,
        [str(e.get("title", ""))[:80] for e in data[:5] if isinstance(e, dict)],
        libs,
        note=f"{deadlines} with close_registration" if deadlines else None,
    )


def ics_events(text: str) -> FeedProbe:
    n = text.count("BEGIN:VEVENT")
    name = re.search(r"^X-WR-CALNAME:(.*)$", text, re.M)
    titles = [t.strip() for t in re.findall(r"^SUMMARY:(.*)$", text, re.M)[:5]]
    return FeedProbe("BEGIN:VCALENDAR" in text[:500], n, name.group(1).strip() if name else None, titles)


# ── national leagues / trivia ────────────────────────────────────────────────────────────────────────

_VOLO = re.compile(r"/discover/([a-z0-9-]+)")


def volo_markets(html: str) -> list[str]:
    return sorted(set(_VOLO.findall(html)) - {"discover"})


_VOLO_TOTAL = re.compile(r"<span>(\d+)</span>\s*<span>ways to play</span>")


def volo_ways_to_play(html: str) -> int | None:
    """A Volo market page's "N ways to play"; ``None`` = not a market page."""
    if m := _VOLO_TOTAL.search(html):
        return int(m.group(1))
    return 0 if 'id="results-grid"' in html else None


_TT_REGION = re.compile(r"teamtrivia\.com/trivia-in-([a-z0-9-]+)")


def teamtrivia_regions(text: str) -> list[str]:
    return sorted(set(_TT_REGION.findall(text)))


def match_region(regions: list[str], name: str, state: str, aliases: list[str]) -> str | None:
    """Team Trivia region slug for a city: by city name/alias, then by state name ("trivia-in-virginia")."""
    wanted = [_norm(n) for n in [name, *aliases]]
    for r in regions:
        if any(w and w in _norm(r) for w in wanted):
            return r
    st = _norm(STATE_NAMES.get(state, ""))
    return next((r for r in regions if st and _norm(r) == st), None)


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def challenge_metros(data: Any, center: tuple[float, float], radius_km: float) -> Counter[str]:
    """Challenge Entertainment's national show list → metro-<slug> classes of shows within the radius."""
    out: Counter[str] = Counter()
    if not isinstance(data, list):
        return out
    for show in data:
        if not isinstance(show, dict):
            continue
        v = show.get("venue") or {}
        try:
            lat, lon = float(str(v.get("latitude"))), float(str(v.get("longitude")))
        except (TypeError, ValueError):
            continue
        if _km(lat, lon, *center) > radius_km:
            continue
        for c in show.get("classes") or []:
            if str(c).startswith("metro-"):
                out[str(c)[6:]] += 1
    return out


def absolute(base: str, href: str) -> str:
    return urljoin(base, href)


def census_county(data: dict[str, Any]) -> str | None:
    """Census geographies/onelineaddress (layers=Counties) → "Maricopa County"."""
    matches = (data.get("result") or {}).get("addressMatches") or []
    if not matches:
        return None
    counties = (matches[0].get("geographies") or {}).get("Counties") or []
    return str(counties[0].get("NAME")) if counties and counties[0].get("NAME") else None


def arcgis_layer(data: dict[str, Any]) -> dict[str, Any] | None:
    """FeatureServer layer ``?f=json`` → {name, date_fields, fields}; None for an error payload."""
    if "error" in data or "fields" not in data:
        return None
    fields = [f for f in data.get("fields") or [] if isinstance(f, dict)]
    dates = [
        str(f["name"])
        for f in fields
        if f.get("type") == "esriFieldTypeDate" and not REFUSE_DATE.search(str(f["name"]))
    ]
    return {"name": data.get("name"), "date_fields": dates, "fields": [str(f.get("name")) for f in fields][:40]}
