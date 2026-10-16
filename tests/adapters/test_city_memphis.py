"""Memphis city units on recorded fixtures (batch D). Landers Center's carbonhouse feed starts with a newline
before the XML declaration, which strict XML parsers reject."""

from __future__ import annotations

from tests.adapters._util import parse, unit

LANDERS = unit("memphis_landers_center")


def test_landers_feed_with_leading_whitespace_parses() -> None:
    parsed = parse(LANDERS, "memphis_landers_center/payload_0.xml")
    assert not parsed.rejects
    evs = [ev for ev, _ in parsed.valid]
    assert len(evs) == 5
    titles = {ev.title for ev in evs}
    assert "23rd Annual Memphis Tri-State Blues Festival" in titles
    games = [ev for ev in evs if ev.title.startswith("Mid-South Monarchs")]
    assert games and all(ev.category == "sports_watch.game" for ev in games)
    assert all(ev.start.tzinfo is not None for ev in evs)
