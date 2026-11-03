"""Institution feeds keep only public-facing families (critique round 2: campus-internal events on city pages)."""

from gotc.pipeline.ingest import campus_allowlist


def test_institution_feeds_keep_public_families_only() -> None:
    p = {"audience_filter": "institution"}
    assert campus_allowlist("music.concert", p) and campus_allowlist("sports_watch.game", p)
    assert not campus_allowlist("nightlife.party", p) and not campus_allowlist("trivia_games.game_night", p)
    assert campus_allowlist("nightlife.party", {**p, "allow_families": ["nightlife"]})
    assert campus_allowlist("nightlife.party", {})  # not an institution feed: untouched


def test_uncategorized_campus_listings_reach_the_gate():
    # 2026-11-02 live run: "Election Security and Administration Seminar" was dropped at ingest as family "other"
    assert campus_allowlist("other.uncategorized", {"audience_filter": "institution"})


def test_a_campus_matchup_classified_as_a_league_becomes_a_game_and_is_kept():
    from datetime import UTC, datetime

    from gotc.adapters.base import Adapter, Payload
    from gotc.pipeline.ingest import parse_payloads
    from tests.conftest import make_city, make_source, unit_for

    class One(Adapter):
        name = "one"

        def fetch(self, ctx):  # pragma: no cover - not used
            raise NotImplementedError

        def parse(self, payload, ctx):
            yield ctx.base("1", title="University of Texas Volleyball vs Ole Miss", category="sports_league.volleyball",
                           start=datetime(2026, 11, 5, 19, tzinfo=UTC))  # fmt: skip

    now = datetime(2026, 11, 2, tzinfo=UTC)
    unit = unit_for(
        make_source("utaustin_events", adapter="localist", audience_filter="institution"), make_city("austin")
    )
    out = parse_payloads(One(), unit, [(Payload(url="u", status=200, content=b"", fetched_at=now), None)], now)
    assert not out.skipped and out.valid[0][0].category == "sports_watch.game"
