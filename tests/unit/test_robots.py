"""RFC 9309 robots.txt semantics: wildcards, '$' anchors, blank lines inside groups, agent precedence."""

from __future__ import annotations

import pytest

from gotc.http.client import RobotsDisallowed
from gotc.http.robots import RobotsRules
from tests.conftest import FixtureTransport
from tests.unit.test_http_client import client

UA = "GetOffTheCouch/0.1 (+https://github.com/lachlanspangler/GetOffTheCouch)"


def test_wildcard_query_rule_disallows_query_urls() -> None:
    # dtjax.com / providenceri.gov layout: the stdlib parser matched "/*?*" literally and allowed these
    r = RobotsRules("User-agent: *\nDisallow: /*?*\nDisallow: /events/\n")
    assert not r.can_fetch(UA, "https://x.example/wp-json/tribe/events/v1/events?page=2")
    assert not r.can_fetch(UA, "https://x.example/events/")
    assert r.can_fetch(UA, "https://x.example/wp-json/tribe/events/v1/events")


def test_dollar_anchor_and_longest_match_wins() -> None:
    r = RobotsRules("User-agent: *\nDisallow: /*.pdf$\nDisallow: /cal\nAllow: /cal/feed.ics\n")
    assert not r.can_fetch(UA, "https://x.example/docs/a.pdf")
    assert r.can_fetch(UA, "https://x.example/docs/a.pdf?v=1")  # '$' anchors the end of the URL
    assert not r.can_fetch(UA, "https://x.example/calendar")
    assert r.can_fetch(UA, "https://x.example/cal/feed.ics")  # longer allow beats shorter disallow


def test_blank_line_does_not_end_the_group() -> None:
    # clpvd.org / LibCal layout: the stdlib parser dropped the Disallow after the blank line
    r = RobotsRules("User-agent: *\nCrawl-delay: 5\n\nDisallow: /wp-json/\n")
    assert not r.can_fetch(UA, "https://x.example/wp-json/tribe/events/v1/events")
    assert r.crawl_delay(UA) == 5.0


def test_specific_agent_group_overrides_star_and_empty_disallow_allows() -> None:
    txt = "User-agent: *\nDisallow: /\n\nUser-agent: GetOffTheCouch\nDisallow:\n"
    assert RobotsRules(txt).can_fetch(UA, "https://x.example/anything")
    other = "User-agent: Googlebot\nDisallow: /\n\nUser-agent: *\nDisallow: /private\n"
    assert RobotsRules(other).can_fetch(UA, "https://x.example/public")
    assert not RobotsRules(other).can_fetch(UA, "https://x.example/private/x")


def test_client_enforces_wildcard_rules(tmp_path) -> None:  # type: ignore[no-untyped-def]
    t = FixtureTransport().add(r"robots\.txt$", "User-agent: *\n\nDisallow: /*?*\n").add(r"/feed", "ok")
    c = client(t, tmp_path)
    assert c.get("https://site.example/feed").text == "ok"
    with pytest.raises(RobotsDisallowed):
        c.get("https://site.example/feed", params={"page": 2})
