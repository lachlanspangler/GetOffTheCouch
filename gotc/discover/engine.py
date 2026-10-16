"""Discovery engine: polite probes → scored candidate units (docs/research/SCALING.md §2.8).

Every request goes through ``PoliteClient`` with ``respect_robots=True`` (structural, not a step to remember —
the §2.10 lesson). On top of that:
  * a hard request budget per run (``--budget-requests``)
  * the ToS denylist (``config/discovery_denylist.yaml``) is checked before any request to a host and on every
    fetched page; Cloudflare challenge pages are a hard exclude and never retried
  * nothing is written to config: the output goes to ``data/discover/<slug>.yaml`` (gitignored), every unit
    ``enabled: false``, for a human or agent to review and promote

Families (``--families``): socrata, datagov, arcgis, library, university, venue, volunteer, leagues, trivia.
"""

from __future__ import annotations

import contextlib
import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import yaml

from gotc.config import CityConfig, load_yaml
from gotc.discover import parse as dp
from gotc.http.client import FetchError, HttpStatusError, PoliteClient, Response, RobotsDisallowed
from gotc.settings import CONFIG_DIR

log = logging.getLogger(__name__)

FAMILIES = ("socrata", "datagov", "arcgis", "library", "university", "venue", "volunteer", "leagues", "trivia")
SOCRATA_CATALOG = "https://api.us.socrata.com/api/catalog/v1"
DATAGOV_SEARCH = "https://catalog.data.gov/search"
HUB_SITES = "https://hub.arcgis.com/api/search/v1/collections/site/items"
ARCGIS_SEARCH = "https://www.arcgis.com/sharing/rest/search"
BC_GATEWAY = "https://gateway.bibliocommons.com/v2/libraries/{code}/rss/events"
VOLO = "https://www.volosports.com"
TEAMTRIVIA_SITEMAP = "https://www.teamtrivia.com/sitemap-locations.php"
CHALLENGE = "https://challengeentertainment.com/wp-json/ce/v1/shows"
CENSUS_GEOGRAPHIES = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"

WEIGHTS = {"works": 0.30, "geo": 0.20, "official": 0.15, "fresh": 0.10, "value": 0.15, "novelty": 0.10}
FAMILY_FILLS = {
    "socrata_events": ["community", "outdoors"],
    "openings": ["openings_parties"],
    "library": ["arts.books", "learning", "family"],
    "university": ["learning", "arts"],
    "venue": ["concerts"],
    "volunteer": ["volunteering"],
    "leagues": ["leagues"],
    "trivia": ["trivia"],
}
OPENING_WORDS = re.compile(
    r"\b(liquor|alcohol|beer|wine|food (service|establishment)|business licen[cs]e|restaurant)\b", re.I
)
EVENT_WORDS = re.compile(
    r"\b(events?|calendar|festivals?|farmers? markets?|special events?|park programs?|block part(y|ies)|parades?|"
    r"street (fair|closure)s?)\b",
    re.I,
)
NOT_EVENTS = re.compile(
    r"\b(building|survey|form|fieldworker|vaccine|road|storm|application|residential|commercial|trade|inspections?|"
    r"sign|sidewalk|right of way|encroachment|grading|demolition|plumbing|electrical|mechanical|fire)\b",
    re.I,
)
DEAD_AFTER = timedelta(days=730)
# hosts with a documented robots exception in docs/SOURCES.md ("Robots exceptions and API usage policies"):
# services*.arcgis.com answers robots.txt with HTTP 403 "Invalid URL" (no policy published)
ROBOTS_EXCEPTIONS = re.compile(r"^services\d*\.arcgis\.com$")


@dataclass
class Denylist:
    hosts: list[str] = field(default_factory=list)
    allow_hosts: list[str] = field(default_factory=list)
    markers: list[str] = field(default_factory=list)

    def host_denied(self, url: str) -> str | None:
        host = urlsplit(url).netloc.lower().split(":")[0]
        if host in self.allow_hosts:
            return None
        return next((h for h in self.hosts if host == h or host.endswith("." + h)), None)

    def page_denied(self, text: str) -> str | None:
        head = text[:200_000]
        return next((m for m in self.markers if m in head), None)


def load_denylist(path: Path = CONFIG_DIR / "discovery_denylist.yaml") -> Denylist:
    data = load_yaml(path.read_text()) or {}
    return Denylist(
        [str(h).lower() for h in data.get("hosts") or []],
        [str(h).lower() for h in data.get("allow_hosts") or []],
        [str(m) for m in data.get("markers") or []],
    )


class BudgetExhausted(Exception):
    pass


@dataclass
class Seed:
    kind: str  # library | university | venue | parks | volunteer | other
    url: str


def parse_seed(raw: str) -> Seed:
    """``kind=URL`` or a bare URL (``.edu`` → university, else other)."""
    kind, _, url = raw.partition("=") if re.match(r"^[a-z]+=https?://", raw) else ("", "", raw)
    if not kind:
        host = urlsplit(raw).netloc.lower()
        kind = "university" if host.endswith(".edu") else "other"
    return Seed(kind, url)


def _slug(s: str, limit: int = 40) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", s.lower())).strip("_")[:limit].strip("_")


def score(
    works: bool,
    geo: float | None,
    official: bool,
    fresh: bool | None,
    fills: list[str],
    lacking: set[str],
    deadlines: bool,
    novel: bool,
) -> tuple[float, dict[str, float]]:
    """SCALING.md §2.8 weights. Unknown geo/freshness earn half credit (we couldn't measure, not "bad")."""
    parts = {
        "works": WEIGHTS["works"] if works else 0.0,
        "geo": WEIGHTS["geo"] * (0.5 if geo is None else max(0.0, min(1.0, geo))),
        "official": WEIGHTS["official"] if official else 0.0,
        "fresh": WEIGHTS["fresh"] * (0.5 if fresh is None else float(fresh)),
        "value": round(WEIGHTS["value"] * ((0.6 if set(fills) & lacking else 0.2) + (0.4 if deadlines else 0.0)), 3),
        "novelty": WEIGHTS["novelty"] if novel else 0.0,
    }
    parts = {k: round(v, 3) for k, v in parts.items()}
    return round(sum(parts.values()), 2), parts


class Discoverer:
    def __init__(
        self,
        city: CityConfig,
        http: PoliteClient,
        now: datetime,
        seeds: list[Seed] | None = None,
        families: tuple[str, ...] = FAMILIES,
        budget: int = 400,
        existing_hosts: set[str] | None = None,
        lacking: set[str] | None = None,
        denylist: Denylist | None = None,
        record: Callable[[str, Response], None] | None = None,
        address: str | None = None,
    ) -> None:
        self.city = city
        self.address = address
        self.context: dict[str, Any] = {}
        self.http = http
        self.now = now
        self.seeds = seeds or []
        self.families = families
        self.budget = budget
        self.used = 0
        self.existing_hosts = existing_hosts or set()
        self.lacking = lacking if lacking is not None else {
            "leagues", "openings_parties", "concerts", "volunteering", "cons_faires", "trivia", "deadlines",
            "community", "outdoors", "arts.books", "learning", "family", "arts",
        }  # fmt: skip
        self.deny = denylist or load_denylist()
        self.record = record
        self.candidates: list[dict[str, Any]] = []
        self.excluded: list[dict[str, Any]] = []
        self.probes: list[dict[str, Any]] = []
        self.blocked_hosts: set[str] = set()
        self._memo: dict[str, Response] = {}
        self.terms = [city.name, *city.aliases]
        self.today = now.astimezone(ZoneInfo(city.timezone)).date()

    # ── polite fetching ─────────────────────────────────────────────────────────────────────────────

    def get(self, url: str, params: dict[str, str | int] | None = None, why: str = "") -> Response | None:
        host = urlsplit(url).netloc.lower()
        if denied := self.deny.host_denied(url):
            self._exclude("tos_denylist", {"url": url}, {"denylist": denied, "why": why})
            return None
        if host in self.blocked_hosts:
            return None  # Cloudflare/robots already said no for this host: never retried
        memo_key = url + "?" + json.dumps(params or {}, sort_keys=True)
        if memo_key in self._memo:
            return self._memo[memo_key]
        if self.used >= self.budget:
            raise BudgetExhausted
        self.used += 1
        entry: dict[str, Any] = {"url": url, "params": dict(params or {}), "why": why}
        try:
            exception = bool(ROBOTS_EXCEPTIONS.match(host))
            if exception:
                entry["robots_exception"] = "documented ArcGIS REST API (docs/SOURCES.md)"
            r = self.http.get(url, params=params, conditional=False, respect_robots=not exception)
        except RobotsDisallowed:
            verdict = self.http.robots_verdict(url)
            cloudflare = dp.is_cloudflare_challenge(self.http.robots_snippet(url), 403)
            reason = "cloudflare" if cloudflare else "robots_disallowed"
            entry |= {"status": None, "verdict": reason, "robots": verdict}
            self.probes.append(entry)
            self.blocked_hosts.add(host)
            note = "robots.txt itself answered with a challenge page" if cloudflare else None
            self._exclude(reason, {"url": url}, {"robots": verdict, "why": why, "note": note})
            return None
        except HttpStatusError as e:
            body = str(e)
            verdict = "cloudflare" if dp.is_cloudflare_challenge(body, e.status) else f"http_{e.status}"
            entry |= {"status": e.status, "verdict": verdict, "robots": self.http.robots_verdict(url)}
            self.probes.append(entry)
            if verdict == "cloudflare":
                self.blocked_hosts.add(host)
                self._exclude("cloudflare", {"url": url}, {"status": e.status, "why": why})
            return None
        except FetchError as e:
            entry |= {"status": None, "verdict": e.kind}
            self.probes.append(entry)
            return None
        entry |= {"status": r.status, "verdict": "ok", "bytes": len(r.content), "robots": self.http.robots_verdict(url)}
        if dp.is_cloudflare_challenge(r.text[:20000], r.status):
            entry["verdict"] = "cloudflare"
            self.blocked_hosts.add(host)
            self._exclude("cloudflare", {"url": url}, {"status": r.status, "why": why})
            self.probes.append(entry)
            return None
        self.probes.append(entry)
        if self.record:
            self.record(url, r)
        self._memo[memo_key] = r
        return r

    def get_json(self, url: str, params: dict[str, str | int] | None = None, why: str = "") -> Any:
        r = self.get(url, params, why)
        if r is None:
            return None
        try:
            return r.json()
        except ValueError:
            self.probes[-1]["verdict"] = "not_json"
            return None

    def _exclude(self, reason: str, hint: dict[str, Any], evidence: dict[str, Any]) -> None:
        self.excluded.append({"confidence": 0.0, "excluded": reason, "unit_hint": hint, "evidence": evidence})

    def _evidence(self, url: str, via: str, **sample: Any) -> dict[str, Any]:
        last: dict[str, Any] = next((p for p in reversed(self.probes) if p["url"] == url), {})
        return {
            "discovered_via": via,
            "probe_url": url,
            "probe_status": last.get("status"),
            "robots": {"host": urlsplit(url).netloc, "verdict": last.get("robots", self.http.robots_verdict(url))},
            "checked_at": self.now.isoformat(timespec="seconds"),
            "sample": sample,
        }

    def _add(
        self,
        unit: dict[str, Any],
        evidence: dict[str, Any],
        *,
        works: bool,
        geo: float | None,
        official: bool,
        fresh: bool | None,
        fills: list[str],
        deadlines: bool = False,
    ) -> None:
        host = urlsplit(str(evidence.get("probe_url", ""))).netloc
        novel = host not in self.existing_hosts
        conf, parts = score(works, geo, official, fresh, fills, self.lacking, deadlines, novel)
        unit = {"enabled": False, **unit}
        unit["id"] = _slug(f"{self.city.slug}_{unit['id']}", 60)
        evidence = {**evidence, "fills": fills, "score": parts}
        if any(c["unit"]["id"] == unit["id"] for c in self.candidates):
            return
        self.candidates.append({"confidence": conf, "unit": unit, "evidence": evidence})

    def geo_share(self, places: list[str]) -> float | None:
        vals = [p for p in places if p]
        if not vals:
            return None
        return round(sum(1 for p in vals if dp.mentions(p, self.terms)) / len(vals), 2)

    def _fresh(self, updated: str | None) -> bool | None:
        if not updated:
            return None
        try:
            dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.now.tzinfo)
        return self.now - dt < timedelta(days=14)

    # ── stages ──────────────────────────────────────────────────────────────────────────────────────

    def run(self) -> dict[str, Any]:
        stages: list[tuple[str, Callable[[], None]]] = [
            ("socrata", self.socrata),
            ("datagov", self.datagov),
            ("arcgis", self.arcgis),
            ("library", self.libraries),
            ("university", self.universities),
            ("venue", self.venues),
            ("volunteer", self.volunteer),
            ("leagues", self.leagues),
            ("trivia", self.trivia),
        ]
        done: list[str] = []
        stopped = None
        with contextlib.suppress(BudgetExhausted):
            self.census_context()
        for name, fn in stages:
            if name not in self.families:
                continue
            try:
                fn()
                done.append(name)
            except BudgetExhausted:
                stopped = f"request budget ({self.budget}) exhausted during {name}"
                break
        self.candidates.sort(key=lambda c: -c["confidence"])
        verdicts: dict[str, int] = {}
        for p in self.probes:
            verdicts[p["verdict"]] = verdicts.get(p["verdict"], 0) + 1
        return {
            "city": self.city.slug,
            "generated_at": self.now.isoformat(timespec="seconds"),
            "center": list(self.city.center),
            "radius_km": self.city.radius_km,
            "context": self.context,
            "families": done,
            "stopped": stopped,
            "requests": {"used": self.used, "budget": self.budget, "by_verdict": verdicts},
            "note": "Candidates only. Every unit is enabled: false; review, set category_map/filters, then promote "
            "into config/cities/<slug>.yaml, record fixtures and add a docs/SOURCES.md row (SCALING.md §2.8).",
            "candidates": self.candidates,
            "excluded": self.excluded,
            "probes": self.probes,
        }

    def census_context(self) -> None:
        """City hall → county (one Census geographies call); the county name joins the place terms, because
        regional portals are often county-run (Maricopa County GIS for Phoenix)."""
        if not self.address:
            return
        data = self.get_json(
            CENSUS_GEOGRAPHIES,
            {"address": self.address, "benchmark": "Public_AR_Current", "vintage": "Current_Current",
             "layers": "Counties", "format": "json"},
            why="Census geographies (county)",
        )  # fmt: skip
        county = dp.census_county(data) if isinstance(data, dict) else None
        self.context = {"address": self.address, "county": county}
        if county:
            self.terms.append(county)
            short = county.removesuffix(" County").removesuffix(" Parish")
            if short != county:
                self.terms.append(short)

    def socrata(self) -> None:
        seen: set[tuple[str, str]] = set()
        terms = ["special events", "events", "permits", "farmers market", "park events", "business license"]
        queries = [f"{self.city.name} {t}" for t in terms] + ["liquor license"]
        for q in queries:
            data = self.get_json(
                SOCRATA_CATALOG, {"q": q, "only": "datasets", "limit": 50}, why=f"socrata catalog: {q}"
            )
            if not isinstance(data, dict):
                continue
            for ds in dp.socrata_catalog(data, self.terms, self.city.state):
                if (ds.domain, ds.id) in seen:
                    continue
                seen.add((ds.domain, ds.id))
                self._socrata_candidate(ds, f"socrata catalog q={q!r}", SOCRATA_CATALOG)

    def _socrata_candidate(self, ds: dp.Dataset, via: str, probe_url: str) -> None:
        name = ds.name
        is_opening = bool(OPENING_WORDS.search(name))
        if not is_opening and not EVENT_WORDS.search(name):
            return
        if is_opening and not (dp.mentions(name, self.terms) or dp.mentions(ds.domain.replace(".", " "), self.terms)):
            # statewide license data: still a candidate (filtered by city later), but say so
            pass
        updated = ds.updated_at
        if updated:
            try:
                age = self.now - datetime.fromisoformat(updated.replace("Z", "+00:00"))
                if age > DEAD_AFTER:
                    self._exclude("dead_dataset", {"adapter": "socrata", "domain": ds.domain, "dataset": ds.id},
                                  {"name": name, "data_updated_at": updated})  # fmt: skip
                    return
            except ValueError:
                pass
        fields = dp.guess_socrata_fields(ds.columns)
        unit: dict[str, Any] = {
            "id": _slug(name, 32),
            "adapter": "socrata",
            "name": name,
            "data_type": "openings" if is_opening else "events",
            "homepage": ds.url or f"https://{ds.domain}/d/{ds.id}",
            "params": {"domain": ds.domain, "dataset": ds.id, "fields": fields, "horizon_days": 60},
        }
        if is_opening:
            unit["params"] |= {
                "kind": "opening",
                "lookback_days": 60,
                "title_template": "{title} — new license",
                "description_template": "License signal, not a confirmed opening date. TODO: describe the "
                "license and its newness date before promoting.",
                "default_category": "food_drink.restaurant_opening",
            }
        else:
            unit["params"]["default_category"] = "community.festival"
        ev = self._evidence(probe_url, via, name=name, data_updated_at=updated, columns=ds.columns[:25],
                            views_last_month=ds.views_last_month, attribution=ds.publisher)  # fmt: skip
        official = ds.domain.endswith(".gov") or ds.domain.startswith(("data.", "opendata.")) or "gov" in ds.domain
        self._add(
            unit,
            ev,
            works="start" in fields,
            geo=1.0 if dp.mentions(f"{ds.domain} {name} {ds.publisher or ''}", self.terms) else None,
            official=official,
            fresh=self._fresh(updated),
            fills=FAMILY_FILLS["openings" if is_opening else "socrata_events"],
        )

    def datagov(self) -> None:
        for q in (f"{self.city.name} events", f"{self.city.name} license"):
            data = self.get_json(DATAGOV_SEARCH, {"q": q, "per_page": 20}, why=f"data.gov search: {q}")
            if not isinstance(data, dict):
                continue
            for ds in dp.datagov_search(data, self.terms):
                if ds.platform == "socrata":
                    self._socrata_candidate(ds, f"data.gov search q={q!r} → Socrata identifier", DATAGOV_SEARCH)
                elif EVENT_WORDS.search(ds.name) or OPENING_WORDS.search(ds.name):
                    self._exclude(
                        "manual_review",
                        {"platform": "data.gov", "title": ds.name, "url": ds.url},
                        {"publisher": ds.publisher, "modified": ds.updated_at, "why": "no adapter mapping for this "
                         "dataset's platform; check the landing page"},
                    )  # fmt: skip

    def arcgis(self) -> None:
        data = self.get_json(HUB_SITES, {"q": f"{self.city.name} open data", "limit": 5}, why="ArcGIS Hub site search")
        if not isinstance(data, dict):
            return
        for site in dp.hub_sites(data, self.terms)[:2]:
            q = f'orgid:{site.org_id} AND type:"Feature Service" AND (permit OR event OR license OR liquor)'
            res = self.get_json(ARCGIS_SEARCH, {"q": q, "num": 50, "f": "json"}, why=f"ArcGIS org search {site.title}")
            if not isinstance(res, dict):
                continue
            probed = 0
            for ds in dp.arcgis_search(res):
                title = ds.name.replace("_", " ")  # "Beer_Permit_Locations": "_" defeats \b
                is_opening = bool(OPENING_WORDS.search(title))
                if (not is_opening and not EVENT_WORDS.search(title)) or NOT_EVENTS.search(title):
                    continue
                layer = f"{(ds.url or '').rstrip('/')}/0"
                fields: dict[str, Any] = {}
                works = False
                if probed < 4:
                    probed += 1
                    meta = self.get_json(layer, {"f": "json"}, why="ArcGIS layer fields")
                    info = dp.arcgis_layer(meta) if isinstance(meta, dict) else None
                    if info is not None:
                        fields = {"start": info["date_fields"][0]} if info["date_fields"] else {}
                        works = bool(info["date_fields"])
                unit: dict[str, Any] = {
                    "id": _slug(ds.name, 32),
                    "adapter": "arcgis",
                    "name": ds.name.replace("_", " "),
                    "data_type": "openings" if is_opening else "events",
                    "homepage": site.url,
                    "params": {
                        "service_url": layer,
                        "fields": fields,
                        "default_category": "food_drink.restaurant_opening" if is_opening else "community.festival",
                        "notes": "TODO: confirm the layer index and map fields from <service_url>?f=json",
                    },
                }
                ev = self._evidence(
                    ARCGIS_SEARCH,
                    f"hub site {site.title!r} (orgId {site.org_id}, owner {site.owner}) → org-scoped search",
                    title=ds.name,
                    owner=ds.publisher,
                    modified=ds.updated_at,
                    views=ds.views_last_month,
                )
                self._add(unit, ev, works=works, geo=1.0, official=True, fresh=self._fresh(ds.updated_at),
                          fills=FAMILY_FILLS["openings" if is_opening else "socrata_events"])  # fmt: skip

    # institutions ----------------------------------------------------------------------------------

    def _seed_pages(self, kinds: tuple[str, ...]) -> list[tuple[Seed, Response, dp.Fingerprint]]:
        out = []
        for seed in [s for s in self.seeds if s.kind in kinds]:
            r = self.get(seed.url, why=f"{seed.kind} seed homepage")
            if r is None:
                continue
            if marker := self.deny.page_denied(r.text):
                self._exclude("tos_denylist", {"url": seed.url}, {"marker": marker})
                continue
            out.append((seed, r, dp.fingerprint(r.text, r.url)))
        return out

    def _bibliocommons(self, code: str, via: str, label: str) -> bool:
        start = self.today.isoformat()
        url = BC_GATEWAY.format(code=code)
        r = self.get(url, {"startDate": start, "endDate": start}, why=f"BiblioCommons code {code}")
        if r is None:
            return False
        p = dp.bibliocommons_rss(r.text)
        if not p.ok:
            return False
        if not p.items:
            self._exclude(
                "no_events", {"adapter": "bibliocommons", "library": code}, {"channel": p.title, "note": p.note}
            )
            return True
        unit = {
            "id": f"{code}_events",
            "adapter": "bibliocommons",
            "name": f"{label or code} events",
            "data_type": "events",
            "params": {
                "library": code,
                "horizon_days": 14,
                "venue_label": label or code,
                "default_category": "arts.books",
            },
        }
        ev = self._evidence(url, via, items_one_day=p.items, channel=p.title, titles=p.sample[:5])
        self._add(unit, ev, works=p.items >= 3, geo=self.geo_share(p.places), official=True, fresh=True,
                  fills=FAMILY_FILLS["library"], deadlines=True)  # fmt: skip
        return True

    def libraries(self) -> None:
        tried: set[str] = set()
        for seed, r, fp in self._seed_pages(("library",)):
            label = (fp.site_name or fp.title or seed.url).split("|")[0].split(" - ")[0].strip()[:60]
            tried |= set(fp.platforms.get("bibliocommons", []))
            self._dispatch(fp, r.url, f"library seed {seed.url}", label, "library", depth=1)
        # name guesses on the gateway (no robots.txt; unknown codes answer 404)
        base = dp._norm(self.city.name)
        for code in dict.fromkeys([base, f"{base}pl", f"{base}library", self.city.slug.replace("_", "")]):
            if code not in tried:
                self._bibliocommons(code, f"BiblioCommons code guessed from the city name ({code})", "")

    def _dispatch(self, fp: dp.Fingerprint, origin: str, via: str, label: str, family: str, depth: int = 0) -> bool:
        """Probe the endpoint of every platform a page fingerprinted; follow events./calendar. hosts once."""
        found = False
        for code in fp.platforms.get("bibliocommons", [])[:2]:
            found |= self._bibliocommons(code, f"{via} links to {code}.bibliocommons.com", label)
        for base in fp.platforms.get("communico", [])[:1]:
            found |= self._communico(base, via, label)
        for host in fp.platforms.get("libcal", [])[:1]:
            found |= self._libcal(host, via, label)
        for name in fp.platforms.get("trumba", [])[:2]:
            found |= self._trumba(name, f"{via} embeds Trumba spud {name}", label, family)
        for host in fp.platforms.get("localist", [])[:1]:
            found |= self._localist(urlsplit(host).netloc, via, label)
        if depth > 0 and not found:
            for host in fp.platforms.get("event_host", [])[:2]:
                r = self.get(host, why=f"events host linked from {via}")
                if r is None:
                    continue
                sub = dp.fingerprint(r.text, r.url)
                if not sub.platforms and "/api/2/" not in r.text:
                    if self._localist(urlsplit(r.url).netloc, via, label):
                        found = True
                    continue
                found |= self._dispatch(sub, r.url, f"{via} → {host}", label, family, depth=0)
        return found

    def _communico(self, base: str, via: str, label: str) -> bool:
        req = {"private": False, "date": self.today.isoformat(), "days": 1, "locations": [], "ages": [], "types": []}
        url = base.rstrip("/") + "/eeventcaldata"
        data = self.get_json(url, {"event_type": 0, "req": json.dumps(req, separators=(",", ":"))}, why="Communico")
        if data is None:
            return False
        p = dp.communico_events(data)
        if not p.ok:
            return False
        # name collisions are real (hcpl = Harford County MD, not Harris County TX): geo fit comes from branches
        unit = {
            "id": _slug(urlsplit(base).netloc.split(".")[0] + "_events", 32),
            "adapter": "communico",
            "name": f"{label} events",
            "data_type": "events",
            "params": {"base_url": base, "horizon_days": 7, "venue_label": label, "default_category": "arts.books"},
        }
        ev = self._evidence(url, f"{via} → Communico", events_one_day=p.items, libraries=p.places[:10],
                            titles=p.sample, deadlines=p.note)  # fmt: skip
        self._add(unit, ev, works=p.items >= 3, geo=self.geo_share(p.places), official=True, fresh=True,
                  fills=FAMILY_FILLS["library"], deadlines=bool(p.note))  # fmt: skip
        return True

    def _libcal(self, host: str, via: str, label: str) -> bool:
        r = self.get(host.rstrip("/") + "/calendar", why="LibCal calendar page (cid)")
        if r is None:
            return False
        cids = dp.fingerprint(r.text, r.url).platforms.get("libcal_cid", [])
        if not cids:
            self._exclude("appointments_only", {"adapter": "ics", "host": host}, {"note": "no public calendar id"})
            return True
        url = f"{host.rstrip('/')}/ical_subscribe.php"
        r2 = self.get(url, {"src": "p", "cid": cids[0]}, why="LibCal ICS")
        if r2 is None:
            return False
        p = dp.ics_events(r2.text)
        unit = {
            "id": _slug(
                urlsplit(host).netloc.split(".")[0] + "_" + urlsplit(host).netloc.split(".")[1] + "_libcal", 40
            ),
            "adapter": "ics",
            "name": f"{label} (LibCal)",
            "data_type": "events",
            # one ICS per public calendar (LibCal has no "all calendars" ICS; rss cid=-1 is empty)
            "params": {
                "url": [f"{url}?src=p&cid={c}" for c in cids[:30]],
                "horizon_days": 30,
                "default_category": "arts.books",
            },
        }
        ev = self._evidence(url, f"{via} → LibCal {host} ({len(cids)} public calendars; probed cid {cids[0]})",
                            calendars=len(cids), vevents_first_calendar=p.items,
                            calname=p.title, titles=p.sample)  # fmt: skip
        self._add(unit, ev, works=p.items >= 3, geo=None, official=True, fresh=None, fills=FAMILY_FILLS["library"])
        return True

    def _trumba(self, name: str, via: str, label: str, family: str) -> bool:
        url = f"https://www.trumba.com/calendars/{name}.json"
        data = self.get_json(url, {"startdate": self.today.strftime("%Y%m%d"), "days": 14}, why="Trumba")
        if data is None:
            return False
        p = dp.trumba_events(data)
        if not p.ok:
            return False
        unit = {
            "id": _slug(f"{name}_trumba", 32),
            "adapter": "trumba",
            "name": f"{label} events",
            "data_type": "events",
            "params": {"webname": name, "horizon_days": 14, "venue_label": label, "organizer": label,
                       "default_category": "arts.books" if family == "library" else "learning.networking"},
        }  # fmt: skip
        ev = self._evidence(url, via, events_14d=p.items, titles=p.sample)
        self._add(unit, ev, works=p.items >= 3, geo=self.geo_share(p.places), official=True, fresh=True,
                  fills=FAMILY_FILLS.get(family, []), deadlines=True)  # fmt: skip
        return True

    def _localist(self, host: str, via: str, label: str) -> bool:
        url = f"https://{host}/api/2/events"
        data = self.get_json(url, {"pp": 5, "days": 14}, why="Localist probe")
        p = dp.localist_events(data) if data is not None else None
        if not (p and p.ok):
            return False
        unit = {
            "id": _slug(host.removeprefix("www.").replace("calendar.", "").replace("events.", "").split(".")[0]
                        + "_events", 32),
            "adapter": "localist",
            "name": f"{label or host} events",
            "data_type": "events",
            "params": {"base_url": f"https://{host}", "horizon_days": 30, "max_pages": 5,
                       "audience_filter": "institution", "default_category": "learning.networking"},
        }  # fmt: skip
        ev = self._evidence(url, f"{via} → Localist", total_14d=p.items, titles=p.sample)
        self._add(unit, ev, works=p.items >= 10, geo=self.geo_share(p.places), official=True, fresh=True,
                  fills=FAMILY_FILLS["university"])  # fmt: skip
        return True

    def _livewhale(self, host: str, via: str, label: str) -> bool:
        url = f"https://{host}/live/json/events/max/5"
        data = self.get_json(url, why="LiveWhale probe")
        p = dp.livewhale_events(data) if data is not None else None
        if not (p and p.ok):
            return False
        unit = {
            "id": _slug(host.removeprefix("events.").split(".")[0] + "_events", 32),
            "adapter": "livewhale",
            "name": f"{label or host} events",
            "data_type": "events",
            "params": {"base_url": f"https://{host}", "max": 200, "audience_filter": "institution",
                       "default_category": "learning.networking"},
        }  # fmt: skip
        ev = self._evidence(url, f"{via} → LiveWhale", sample_items=p.items, titles=p.sample)
        self._add(unit, ev, works=p.items >= 1, geo=None, official=True, fresh=True, fills=FAMILY_FILLS["university"])
        return True

    def universities(self) -> None:
        for seed in [s for s in self.seeds if s.kind == "university"]:
            domain = urlsplit(seed.url).netloc.lower().removeprefix("www.")
            via = f"university seed {seed.url}"
            if any(self._localist(h, via, domain) for h in (f"calendar.{domain}", f"events.{domain}")):
                continue
            if self._livewhale(f"events.{domain}", via, domain):
                continue
            # last resort: fingerprint the homepage (Trumba spuds, linked events./calendar. hosts …)
            for _, r, fp in self._seed_pages_one(seed):
                self._dispatch(fp, r.url, via, domain, "university", depth=1)

    def _seed_pages_one(self, seed: Seed) -> list[tuple[Seed, Response, dp.Fingerprint]]:
        saved, self.seeds = self.seeds, [seed]
        try:
            return self._seed_pages((seed.kind,))
        finally:
            self.seeds = saved

    def venues(self) -> None:
        for seed, r, fp in self._seed_pages(("venue", "parks", "other")):
            origin = f"{urlsplit(r.url).scheme}://{urlsplit(r.url).netloc}"
            label = (fp.site_name or fp.title or origin).split("|")[0].strip()[:60]
            if fp.wordpress or "tribe" in fp.platforms:
                ns = self.get_json(f"{origin}/wp-json/", why="WordPress namespaces")
                if dp.wp_has_tribe(ns):
                    url = f"{origin}/wp-json/tribe/events/v1/events"
                    data = self.get_json(url, {"start_date": self.today.isoformat(), "per_page": 5}, why="Tribe events")
                    p = dp.tribe_events(data)
                    if p.ok:
                        unit: dict[str, Any] = {
                            "id": _slug(urlsplit(origin).netloc.removeprefix("www.").split(".")[0], 32),
                            "adapter": "tribe",
                            "name": label,
                            "data_type": "concerts" if seed.kind == "venue" else "events",
                            "params": {"base_url": origin, "horizon_days": 60, "per_page": 50, "max_pages": 6,
                                       "organizer": label,
                                       "default_category": "music.concert" if seed.kind == "venue" else "outdoors.park"},
                        }  # fmt: skip
                        ev = self._evidence(url, f"{seed.kind} seed {seed.url} → wp-json tribe/events/v1",
                                            total=p.items, titles=p.sample)  # fmt: skip
                        self._add(unit, ev, works=p.items >= 5, geo=self.geo_share(p.places),
                                  official=urlsplit(origin).netloc.endswith((".gov", ".org")), fresh=True,
                                  fills=FAMILY_FILLS["venue" if seed.kind == "venue" else "socrata_events"])  # fmt: skip
                        continue
            if seed.kind == "venue":
                url = f"{origin}/events/rss"
                rr = self.get(url, why="carbonhouse RSS")
                if rr is not None:
                    p = dp.carbonhouse_rss(rr.text)
                    if p.ok and p.items and not p.note:
                        unit = {
                            "id": _slug(urlsplit(origin).netloc.removeprefix("www.").split(".")[0], 32),
                            "adapter": "rss_events",
                            "name": label,
                            "data_type": "concerts",
                            "params": {"url": url, "horizon_days": 180, "spectator_venue": True, "organizer": label,
                                       "venue": {"name": label, "address": "TODO"}, "default_category": "music.concert"},
                        }  # fmt: skip
                        ev = self._evidence(url, f"venue seed {seed.url} → carbonhouse /events/rss", items=p.items,
                                            titles=p.sample)  # fmt: skip
                        self._add(unit, ev, works=p.items >= 5, geo=1.0, official=False, fresh=True,
                                  fills=FAMILY_FILLS["venue"])  # fmt: skip
                        continue
            depth = 0 if seed.kind == "venue" else 1
            self._dispatch(fp, r.url, f"{seed.kind} seed {seed.url}", label, "socrata_events", depth=depth)
            if fp.jsonld_events:
                unit = {
                    "id": _slug(urlsplit(origin).netloc.removeprefix("www.").split(".")[0] + "_jsonld", 32),
                    "adapter": "jsonld",
                    "name": label,
                    "data_type": "events",
                    "params": {"urls": [seed.url], "organizer": label, "default_category": "community.festival"},
                }
                ev = self._evidence(seed.url, f"{seed.kind} seed page carries schema.org Event JSON-LD",
                                    jsonld_events=fp.jsonld_events, site_name=fp.site_name)  # fmt: skip
                self._add(unit, ev, works=fp.jsonld_events >= 3, geo=None, official=False, fresh=None,
                          fills=FAMILY_FILLS["socrata_events"])  # fmt: skip
            for host in fp.platforms.get("registration_platform", [])[:2]:
                self._exclude("manual_review", {"platform": host, "seed": seed.url},
                              {"note": "recreation registration platform (real deadlines); read its ToS before any adapter"})  # fmt: skip
            if "civicplus" in fp.platforms:
                self._exclude("no_adapter_yet", {"platform": "civicplus", "url": seed.url},
                              {"note": "CivicPlus calendar RSS (RSSFeed.aspx?ModID=58) — adapter idea in the ledger"})  # fmt: skip

    def volunteer(self) -> None:
        tenants: list[tuple[str, str]] = []
        for seed, _, fp in self._seed_pages(("volunteer",)):
            for t in fp.platforms.get("galaxydigital", [])[:1]:
                tenants.append((t, f"volunteer seed {seed.url} links to {t}"))
            if "handsonconnect" in fp.platforms:
                block = fp.platforms["handsonconnect"][0]
                origin = f"{urlsplit(seed.url).scheme}://{urlsplit(seed.url).netloc}"
                unit = {
                    "id": _slug(urlsplit(origin).netloc.removeprefix("www.").split(".")[0] + "_volunteer", 32),
                    "adapter": "handsonconnect",
                    "name": f"{fp.site_name or urlsplit(origin).netloc} volunteer opportunities",
                    "data_type": "volunteer",
                    "params": {"base_url": origin, "horizon_days": 14, "window_days": 2}
                    | ({"block_id": int(block)} if block else {}),
                }
                ev = self._evidence(seed.url, "volunteer seed page is a HandsOn Connect site", block_id=block or None)
                self._add(unit, ev, works=False, geo=1.0, official=False, fresh=None, fills=FAMILY_FILLS["volunteer"],
                          deadlines=True)  # fmt: skip
        base = dp._norm(self.city.name)
        for guess in (f"volunteer{base}", f"handson{base}", f"{base}volunteers"):
            tenants.append(
                (f"https://{guess}.galaxydigital.com", f"Galaxy Digital tenant guessed from the city name ({guess})")
            )
        seen: set[str] = set()
        for tenant, via in tenants:
            if tenant in seen:
                continue
            seen.add(tenant)
            url = f"{tenant}/need/rss/"
            r = self.get(url, why="Galaxy Digital RSS")
            if r is None:
                continue
            p = dp.galaxy_rss(r.text)
            if not p.ok or not p.items:
                continue
            unit = {
                "id": _slug(urlsplit(tenant).netloc.split(".")[0], 32),
                "adapter": "galaxydigital",
                "name": p.title or urlsplit(tenant).netloc,
                "data_type": "volunteer",
                "params": {"base_url": tenant, "max_details": 15, "max_shifts": 6},
            }
            ev = self._evidence(url, via, items=p.items, channel=p.title, titles=p.sample)
            self._add(unit, ev, works=p.items >= 3, geo=None, official=False, fresh=True, fills=FAMILY_FILLS["volunteer"],
                      deadlines=True)  # fmt: skip

    def leagues(self) -> None:
        r = self.get(f"{VOLO}/discover", why="Volo market list")
        markets = dp.volo_markets(r.text) if r is not None else []
        guess = re.sub(r"[^a-z0-9]+", "-", self.city.name.lower()).strip("-")
        slug = next((m for m in markets if m == guess or m.startswith(guess)), guess)
        url = f"{VOLO}/discover/{slug}"
        page = self.get(url, {"category": "leagues"}, why="Volo market page")
        total = dp.volo_ways_to_play(page.text) if page is not None else None
        if total:
            unit = {
                "id": "volo",
                "adapter": "volo",
                "name": f"Volo Sports {self.city.name}",
                "data_type": "leagues",
                "params": {"base_url": VOLO, "city_slug": slug, "include_fees": True, "max_pages": 6},
            }
            ev = self._evidence(url, "volosports.com/discover market list" if slug in markets else "Volo slug probe",
                                ways_to_play=total, listed_on_discover=slug in markets)  # fmt: skip
            self._add(
                unit, ev, works=True, geo=1.0, official=False, fresh=True, fills=FAMILY_FILLS["leagues"], deadlines=True
            )
        elif page is not None or r is not None:
            self._exclude("no_market", {"adapter": "volo", "city_slug": slug}, {"markets": markets})

    def trivia(self) -> None:
        r = self.get(TEAMTRIVIA_SITEMAP, why="Team Trivia sitemap")
        if r is not None:
            regions = dp.teamtrivia_regions(r.text)
            region = dp.match_region(regions, self.city.name, self.city.state, self.city.aliases)
            if region:
                unit = {
                    "id": "teamtrivia",
                    "adapter": "teamtrivia",
                    "name": f"Team Trivia {self.city.name}",
                    "data_type": "recurring",
                    "params": {"base_url": "https://www.teamtrivia.com", "regions": {self.city.slug: region},
                               "max_venues": 60},
                }  # fmt: skip
                ev = self._evidence(TEAMTRIVIA_SITEMAP, "teamtrivia.com sitemap-locations.php", region=region,
                                    regions_listed=len(regions))  # fmt: skip
                self._add(unit, ev, works=True, geo=None, official=False, fresh=None, fills=FAMILY_FILLS["trivia"])
        data = self.get_json(CHALLENGE, why="Challenge Entertainment national show list")
        if data is not None:
            metros = dp.challenge_metros(data, self.city.center, self.city.radius_km)
            if metros:
                top = [m for m, n in metros.most_common(3) if n >= 2]
                unit = {
                    "id": "challenge_trivia",
                    "adapter": "challenge",
                    "name": f"Challenge Entertainment trivia & bingo ({self.city.name})",
                    "data_type": "recurring",
                    "params": {"url": CHALLENGE, "metros": top or [metros.most_common(1)[0][0]]},
                }
                ev = self._evidence(CHALLENGE, "national feed filtered to the city radius", shows_in_radius=sum(metros.values()),
                                    metro_classes=dict(metros.most_common(5)))  # fmt: skip
                self._add(unit, ev, works=sum(metros.values()) >= 5, geo=1.0, official=False, fresh=True,
                          fills=FAMILY_FILLS["trivia"])  # fmt: skip


def existing_hosts(city: CityConfig) -> set[str]:
    hosts: set[str] = set()
    for s in city.sources:
        for v in [s.homepage, *[str(x) for x in s.params.values() if isinstance(x, str)]]:
            if v and v.startswith("http"):
                hosts.add(urlsplit(v).netloc.lower())
        if s.adapter == "bibliocommons":
            hosts.add("gateway.bibliocommons.com")
    return hosts


def write_candidates(doc: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# gotc discover {doc['city']} — generated {doc['generated_at']}. NOT loaded by `gotc run`.\n"
        "# Review, edit, and paste chosen units into config/cities/<slug>.yaml (SCALING.md §2.8).\n"
    )
    path.write_text(header + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=110))
