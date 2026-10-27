"""Institution feeds keep only public-facing families (critique round 2: campus-internal events on city pages)."""

from gotc.pipeline.ingest import campus_allowlist


def test_institution_feeds_keep_public_families_only() -> None:
    p = {"audience_filter": "institution"}
    assert campus_allowlist("music.concert", p) and campus_allowlist("sports_watch.game", p)
    assert not campus_allowlist("nightlife.party", p) and not campus_allowlist("trivia_games.game_night", p)
    assert campus_allowlist("nightlife.party", {**p, "allow_families": ["nightlife"]})
    assert campus_allowlist("nightlife.party", {})  # not an institution feed: untouched
