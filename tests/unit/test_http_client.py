import httpx
import pytest

from gotc.http.client import HttpStatusError, PoliteClient, RobotsDisallowed
from tests.conftest import FixtureTransport


def client(t, tmp_path, **kw):
    return PoliteClient(transport=t, sleep=lambda s: None, cache_dir=tmp_path / "cache", min_interval_s=0, **kw)


def test_retries_5xx_then_succeeds(tmp_path):
    n = {"i": 0}

    def flaky(req):
        n["i"] += 1
        return httpx.Response(503 if n["i"] < 3 else 200, json={"ok": True})

    t = FixtureTransport().add_fn(r"api\.example\.com/x", flaky)
    assert client(t, tmp_path).get_json("https://api.example.com/x", respect_robots=False) == {"ok": True}
    assert n["i"] == 3


def test_4xx_is_not_retried_and_is_typed(tmp_path):
    t = FixtureTransport().add(r"/gone", status=404)
    with pytest.raises(HttpStatusError) as e:
        client(t, tmp_path).get("https://api.example.com/gone", respect_robots=False)
    assert e.value.kind == "not_found"
    assert len([c for c in t.calls if "gone" in c]) == 1


def test_gives_up_after_max_attempts(tmp_path):
    t = FixtureTransport().add(r"/down", status=500)
    with pytest.raises(HttpStatusError) as e:
        client(t, tmp_path, max_attempts=3).get("https://api.example.com/down", respect_robots=False)
    assert e.value.kind == "server_error"
    assert len(t.calls) == 3


def test_robots_disallow_is_enforced(tmp_path):
    t = FixtureTransport().add(r"robots\.txt$", "User-agent: *\nDisallow: /private\n").add(r"/public", "ok")
    c = client(t, tmp_path)
    assert c.get("https://site.example/public").text == "ok"
    with pytest.raises(RobotsDisallowed):
        c.get("https://site.example/private/page")


def test_robots_403_means_disallow_all(tmp_path):
    t = FixtureTransport().add(r"robots\.txt$", status=403)
    with pytest.raises(RobotsDisallowed):
        client(t, tmp_path).get("https://blocked.example/anything")


def test_conditional_get_uses_etag_and_serves_cached_body_on_304(tmp_path):
    def handler(req):
        if req.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304)
        return httpx.Response(200, content=b"BODY", headers={"ETag": '"v1"'})

    t = FixtureTransport().add_fn(r"/feed\.ics", handler)
    c = client(t, tmp_path)
    first = c.get("https://cal.example/feed.ics", respect_robots=False)
    second = c.get("https://cal.example/feed.ics", respect_robots=False)
    assert first.content == second.content == b"BODY"
    assert second.from_cache and not first.from_cache


def test_secrets_are_redacted_from_urls_and_errors(tmp_path):
    t = FixtureTransport().add(r"/events", {"a": 1}).add(r"/bad", status=401)
    c = client(t, tmp_path)
    r = c.get("https://api.example.com/events", params={"apikey": "SECRET123"}, respect_robots=False)
    assert "SECRET123" not in r.url
    with pytest.raises(HttpStatusError) as e:
        c.get("https://api.example.com/bad", params={"client_id": "SECRET456"}, respect_robots=False)
    assert "SECRET456" not in str(e.value)
    assert e.value.kind == "auth"


def test_per_source_rate_limit_applies_to_its_hosts(tmp_path):
    from gotc.pipeline.ingest import apply_rate_limit
    from tests.conftest import make_city, make_source, unit_for

    src = make_source("x", "tribe", base_url="https://parks.example.org")
    src.min_interval_s = 6
    c = client(FixtureTransport(), tmp_path)
    apply_rate_limit(c, unit_for(src, make_city()))
    assert c.host_intervals["parks.example.org"] == 6


def test_post_sends_form_and_honors_robots(tmp_path):
    seen = {}

    def handler(req):
        seen["method"] = req.method
        seen["body"] = req.content.decode()
        return httpx.Response(200, json={"code": 200})

    t = (
        FixtureTransport()
        .add(r"robots\.txt$", "User-agent: *\nDisallow: /private\n")
        .add_fn(r"/search/getOpportunitiesCalendar", handler)
    )
    c = client(t, tmp_path)
    r = c.post("https://hoc.example/search/getOpportunitiesCalendar", data={"a": "2026-10-17", "n": 5})
    assert r.json() == {"code": 200}
    assert seen["method"] == "POST" and seen["body"] == "a=2026-10-17&n=5"
    with pytest.raises(RobotsDisallowed):
        c.post("https://hoc.example/private/search", data={"a": 1})


def test_post_retries_5xx_and_is_never_cached(tmp_path):
    n = {"i": 0}

    def flaky(req):
        n["i"] += 1
        return httpx.Response(503 if n["i"] == 1 else 200, content=b"OK", headers={"ETag": '"v1"'})

    t = FixtureTransport().add_fn(r"/search", flaky)
    c = client(t, tmp_path)
    assert c.post("https://api.example.com/search", data={"q": 1}, respect_robots=False).text == "OK"
    assert c.post("https://api.example.com/search", data={"q": 1}, respect_robots=False).text == "OK"
    assert n["i"] == 3  # one retry, then a fresh request (no conditional cache for POST)
    assert not (tmp_path / "cache").exists()


def test_post_redacts_secrets_in_errors(tmp_path):
    t = FixtureTransport().add(r"/bad", status=403)
    with pytest.raises(HttpStatusError) as e:
        client(t, tmp_path).post("https://api.example.com/bad", params={"token": "S3CRET"}, respect_robots=False)
    assert "S3CRET" not in str(e.value) and e.value.kind == "forbidden"


def test_cookies_are_never_stored(tmp_path):
    """Volo/Galaxy redirect cookie-carrying requests to a remembered view (dropping ?page=N)."""

    def setter(req):
        return httpx.Response(200, content=b"x", headers={"Set-Cookie": "session=abc; Path=/"})

    def checker(req):
        return httpx.Response(200, content=req.headers.get("cookie", "").encode())

    t = FixtureTransport().add_fn(r"/first", setter).add_fn(r"/second", checker)
    c = client(t, tmp_path)
    c.get("https://site.example/first", respect_robots=False)
    assert c.get("https://site.example/second", respect_robots=False).text == ""
