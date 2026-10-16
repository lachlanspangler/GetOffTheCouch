"""A polite HTTP client: rate-limited per host, robots-aware, retrying with backoff, conditional-GET cached.

Every adapter fetches through this. ``get`` for pages/feeds/APIs; ``post`` only for read-only search
endpoints that require it (HandsOn Connect). Cookies are never stored (stateless, first-visit view). Tests inject an ``httpx.MockTransport`` (see tests/fixtures.py) so the
suite never touches the live internet.

Errors are typed so the health system can tell *why* a source failed:
  HttpStatusError (403/404/5xx…), RobotsDisallowed, FetchTimeout, FetchError (network).
"""

from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from http.cookiejar import CookieJar, DefaultCookiePolicy
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from gotc.settings import Settings

REDACT_KEYS = ("apikey", "client_id", "client_secret", "app_id", "token", "key")


class _NoCookies(DefaultCookiePolicy):
    """Stateless crawling: never store cookies. Some sites (Volo, Galaxy Digital) redirect cookie-carrying
    requests to a 'remembered' view (dropping ?page=N or the detail page), so a cookie jar silently changes
    what we fetch. Every request is made as a first-time visitor."""

    def set_ok(self, cookie: Any, request: Any) -> bool:
        return False


class FetchError(Exception):
    """Base for every fetch failure. ``kind`` is the health-system failure class."""

    kind = "network"

    def __init__(self, message: str, url: str) -> None:
        super().__init__(message)
        self.url = url


class HttpStatusError(FetchError):
    def __init__(self, status: int, url: str, body_snippet: str = "") -> None:
        super().__init__(f"HTTP {status} for {url}: {body_snippet[:200]}", url)
        self.status = status
        self.kind = {
            401: "auth",
            403: "forbidden",
            404: "not_found",
            410: "not_found",
            429: "rate_limited",
        }.get(status, "server_error" if status >= 500 else "http_error")


class RobotsDisallowed(FetchError):
    kind = "robots_disallowed"


class FetchTimeout(FetchError):
    kind = "timeout"


@dataclass
class Response:
    url: str
    status: int
    headers: Mapping[str, str]
    content: bytes
    from_cache: bool = False
    elapsed_ms: int = 0

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.content)


@dataclass
class _HostState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    next_ok: float = 0.0
    robots: RobotFileParser | None = None
    robots_checked: bool = False


class PoliteClient:
    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
        min_interval_s: float = 1.0,
        max_attempts: int = 4,
        timeout_s: float = 30.0,
        sleep: Callable[[float], None] = time.sleep,
        cache_dir: Path | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self._client = httpx.Client(
            transport=transport,
            timeout=timeout_s,
            follow_redirects=True,
            cookies=CookieJar(policy=_NoCookies()),
            headers={"User-Agent": self.settings.user_agent, "Accept-Encoding": "gzip, deflate"},
        )
        self.min_interval_s = min_interval_s
        self.max_attempts = max_attempts
        self._sleep = sleep
        self._hosts: dict[str, _HostState] = {}
        self._cache_dir = cache_dir if cache_dir is not None else self.settings.http_cache_dir
        self.request_count = 0
        self.host_intervals: dict[str, float] = {}

    # ── public ──────────────────────────────────────────────────────────

    def get(
        self,
        url: str,
        params: Mapping[str, str | int | float] | None = None,
        headers: Mapping[str, str] | None = None,
        respect_robots: bool = True,
        conditional: bool = True,
        redact: tuple[str, ...] = REDACT_KEYS,
    ) -> Response:
        return self._request("GET", url, params, headers, None, respect_robots, conditional, redact)

    def post(
        self,
        url: str,
        data: Mapping[str, str | int | float] | None = None,
        params: Mapping[str, str | int | float] | None = None,
        headers: Mapping[str, str] | None = None,
        respect_robots: bool = True,
        redact: tuple[str, ...] = REDACT_KEYS,
        files: Mapping[str, tuple[str, bytes, str]] | None = None,
    ) -> Response:
        """Form-encoded (or multipart, with ``files``) POST (search endpoints that only accept POST). Same robots check, per-host throttle,
        retry/backoff and URL redaction as ``get``; never cached (POST responses aren't conditional-GETable).
        Only use for read-only search/query endpoints — never to submit anything on a user's behalf."""
        return self._request("POST", url, params, headers, dict(data or {}), respect_robots, False, redact, files)

    def _request(
        self,
        method: str,
        url: str,
        params: Mapping[str, str | int | float] | None,
        headers: Mapping[str, str] | None,
        data: dict[str, str | int | float] | None,
        respect_robots: bool,
        conditional: bool,
        redact: tuple[str, ...],
        files: Mapping[str, tuple[str, bytes, str]] | None = None,
    ) -> Response:
        # merge, don't replace: httpx.URL(url, params={}) silently drops an existing ?query (Luma ICS, Maker Faire)
        full = str(httpx.URL(url).copy_merge_params(dict(params)) if params else httpx.URL(url))
        safe = _redact(full, redact)
        if respect_robots:
            self._check_robots(full)
        cache_key = hashlib.sha256(safe.encode()).hexdigest()[:24]
        cached = self._cache_load(cache_key) if conditional else None
        hdrs = dict(headers or {})
        if cached:
            if etag := cached["headers"].get("etag"):
                hdrs["If-None-Match"] = etag
            if lm := cached["headers"].get("last-modified"):
                hdrs["If-Modified-Since"] = lm
        form = {k: str(v) for k, v in data.items()} if data is not None else None

        last_exc: FetchError | None = None
        for attempt in range(1, self.max_attempts + 1):
            self._throttle(full)
            t0 = time.monotonic()
            try:
                r = self._client.request(method, full, headers=hdrs, data=form, files=dict(files) if files else None)
            except httpx.TimeoutException:
                last_exc = FetchTimeout(f"timeout fetching {safe}", safe)
            except httpx.HTTPError as e:
                last_exc = FetchError(f"{type(e).__name__}: {e}", safe)
            else:
                self.request_count += 1
                ms = int((time.monotonic() - t0) * 1000)
                if r.status_code == 304 and cached:
                    body = (self._cache_dir / f"{cache_key}.body").read_bytes()
                    return Response(safe, 200, cached["headers"], body, from_cache=True, elapsed_ms=ms)
                if r.status_code < 400:
                    resp = Response(
                        _redact(str(r.url), redact), r.status_code, dict(r.headers), r.content, elapsed_ms=ms
                    )
                    if conditional:
                        self._cache_store(cache_key, resp)
                    return resp
                last_exc = HttpStatusError(r.status_code, safe, r.text)
                if r.status_code not in (408, 425, 429, 500, 502, 503, 504):
                    raise last_exc
                if attempt < self.max_attempts:
                    self._sleep(self._retry_after(r) or self._backoff(attempt))
                    continue
            if attempt < self.max_attempts:
                self._sleep(self._backoff(attempt))
        assert last_exc is not None
        raise last_exc

    def get_json(self, url: str, **kw: Any) -> Any:
        return self.get(url, **kw).json()

    def close(self) -> None:
        self._client.close()

    # ── politeness ──────────────────────────────────────────────────────

    def _host(self, url: str) -> tuple[str, _HostState]:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        return host, self._hosts.setdefault(host, _HostState())

    def _throttle(self, url: str) -> None:
        _, st = self._host(url)
        interval = self.host_intervals.get(urlsplit(url).netloc, self.min_interval_s)
        with st.lock:
            wait = st.next_ok - time.monotonic()
            if wait > 0:
                self._sleep(wait)
            st.next_ok = time.monotonic() + interval

    def _check_robots(self, url: str) -> None:
        host, st = self._host(url)
        if not st.robots_checked:
            st.robots_checked = True
            try:
                r = self._client.get(f"{host}/robots.txt")
                if r.status_code < 400:
                    rp = RobotFileParser()
                    rp.parse(r.text.splitlines())
                    st.robots = rp
                    if (delay := rp.crawl_delay(self.settings.user_agent)) is not None:
                        self.host_intervals[urlsplit(url).netloc] = max(float(delay), self.min_interval_s)
                elif r.status_code in (401, 403):
                    # RFC 9309 §2.3.1.3: unreachable-because-forbidden robots → assume full disallow
                    rp = RobotFileParser()
                    rp.parse(["User-agent: *", "Disallow: /"])
                    st.robots = rp
            except httpx.HTTPError:
                st.robots = None  # unreachable robots.txt → allowed (RFC 9309 §2.3.1.4)
        if st.robots and not st.robots.can_fetch(self.settings.user_agent, url):
            raise RobotsDisallowed(f"robots.txt disallows {url}", url)

    def _backoff(self, attempt: int) -> float:
        return float(min(60.0, (2 ** (attempt - 1)) * 1.5 + random.uniform(0, 1)))

    @staticmethod
    def _retry_after(r: httpx.Response) -> float | None:
        ra = r.headers.get("retry-after")
        if not ra:
            return None
        try:
            return min(120.0, float(ra))
        except ValueError:
            try:
                return max(0.0, min(120.0, parsedate_to_datetime(ra).timestamp() - time.time()))
            except (TypeError, ValueError):
                return None

    # ── conditional-GET cache ───────────────────────────────────────────

    def _cache_load(self, key: str) -> dict[str, Any] | None:
        meta = self._cache_dir / f"{key}.json"
        if not meta.exists() or not (self._cache_dir / f"{key}.body").exists():
            return None
        try:
            data: dict[str, Any] = json.loads(meta.read_text())
            return data
        except (OSError, json.JSONDecodeError):
            return None

    def _cache_store(self, key: str, resp: Response) -> None:
        h = {k.lower(): v for k, v in resp.headers.items() if k.lower() in ("etag", "last-modified")}
        if not h:
            return
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        (self._cache_dir / f"{key}.body").write_bytes(resp.content)
        (self._cache_dir / f"{key}.json").write_text(json.dumps({"url": resp.url, "headers": h}))


def _redact(url: str, keys: tuple[str, ...]) -> str:
    u = httpx.URL(url)
    if not u.params:
        return url
    params = [(k, "REDACTED" if k.lower() in keys else v) for k, v in u.params.multi_items()]
    return str(u.copy_with(params=params))
