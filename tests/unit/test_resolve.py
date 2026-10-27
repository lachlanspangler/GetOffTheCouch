from datetime import UTC, datetime, timedelta

from gotc.pipeline.resolve import cluster_events, match_score, resolve_venues
from gotc.pipeline.textnorm import norm_title, norm_venue, title_similarity
from gotc.schema import SourceEvent
from tests.conftest import make_city

T = datetime(2026, 11, 1, 1, 0, tzinfo=UTC)


def ev(source, rid, title, start=T, venue=None, lat=None, lon=None, **kw):
    return SourceEvent(
        source_id=source,
        record_id=rid,
        city="testville",
        title=title,
        category="music.concert",
        start=start,
        timezone="America/Chicago",
        fetched_at=T,
        location={"venue_name": venue, "lat": lat, "lon": lon},
        **kw,
    )


def test_title_normalization():
    assert norm_title("Phoebe Bridgers presents: The Reunion Tour 2026 | Tickets") == "phoebe bridgers reunion"
    assert title_similarity("Big Thief - Live in Concert", "BIG THIEF") > 0.95
    assert title_similarity("Big Thief", "Bon Iver") < 0.6


def test_venue_normalization():
    assert norm_venue("The Fillmore Minneapolis") == norm_venue("Fillmore")
    assert norm_venue("First Avenue & 7th St Entry") != norm_venue("Orpheum Theatre")


def test_same_concert_on_two_sites_matches():
    a = ev("ticketmaster", "1", "Big Thief", venue="First Avenue", lat=44.9784, lon=-93.2761)
    b = ev(
        "seatgeek",
        "x",
        "Big Thief with special guest",
        start=T + timedelta(minutes=30),
        venue="First Avenue - Mainroom",
        lat=44.9785,
        lon=-93.2760,
    )
    assert match_score(a, b, None, None) >= 0.85


def test_different_shows_same_venue_same_night_do_not_match():
    a = ev("ticketmaster", "1", "Big Thief", venue="First Avenue")
    b = ev("seatgeek", "x", "Japanese Breakfast", venue="First Avenue")
    assert match_score(a, b, None, None) == 0.0


def test_same_title_far_apart_in_time_does_not_match():
    a = ev("ticketmaster", "1", "Big Thief", venue="First Avenue")
    b = ev("seatgeek", "x", "Big Thief", start=T + timedelta(hours=5), venue="First Avenue")
    assert match_score(a, b, None, None) == 0.0


def test_same_source_never_merges():
    a = ev("ticketmaster", "1", "Big Thief", venue="First Avenue")
    b = ev("ticketmaster", "2", "Big Thief", venue="First Avenue")
    assert match_score(a, b, None, None) == 0.0


def test_cluster_three_sources_into_one_and_keep_others_separate():
    items = [
        ev("ticketmaster", "1", "Big Thief", venue="First Avenue", lat=44.9784, lon=-93.2761),
        ev("seatgeek", "a", "Big Thief", venue="First Ave", lat=44.9784, lon=-93.2761),
        ev("venue_ics", "z", "BIG THIEF (sold out)", venue="First Avenue"),
        ev("seatgeek", "b", "Mitski", venue="Orpheum Theatre", lat=44.9761, lon=-93.2747),
    ]
    city = make_city()
    venues = []
    vof = resolve_venues(items, city, venues)
    clusters = cluster_events(items, vof, city.timezone)
    sizes = sorted(len(c.members) for c in clusters)
    assert sizes == [1, 3]
    big = next(c for c in clusters if len(c.members) == 3)
    assert big.members[0].source_id == "ticketmaster"  # most trusted first


def test_venue_resolution_merges_aliases_by_name_and_proximity():
    items = [
        ev("a", "1", "Show X", venue="The Fillmore Minneapolis", lat=44.99, lon=-93.27),
        ev("b", "2", "Show Y", venue="Fillmore", lat=44.99, lon=-93.27),
    ]
    vof = resolve_venues(items, make_city(), [])
    assert vof["a|1"] == vof["b|2"]


def test_curated_alias_wins_over_a_venue_stored_by_an_earlier_build():
    from gotc.pipeline.resolve import VenueEntity

    name = "DC Public Library – Southwest Neighborhood Library"
    curated = VenueEntity("ven_cur", "Southwest Library", "southwest library", 38.88, -77.02, "900 Wesley Pl SW")
    alias = VenueEntity(**{**curated.__dict__, "norm": norm_venue(name)})
    # an earlier build stored the feed's name as its own (coordinate-less) venue, listed after the curated entries
    stored = VenueEntity("ven_old", name, norm_venue(name))
    items = [ev("dcpl", "1", "Story time", venue=name)]
    vof = resolve_venues(items, make_city(), [curated, alias, stored])
    assert vof["dcpl|1"] == "ven_cur"


def test_ids_stay_unique_when_a_cluster_splits(db):
    from gotc.pipeline.resolve import Cluster, assign_ids

    a = ev("ticketmaster", "1", "Big Thief", venue="First Avenue")
    b = ev("seatgeek", "x", "Big Thief", venue="First Avenue")
    first = assign_ids(db, "testville", [Cluster(members=[a, b], scores=[1, 1])])
    ((eid, _),) = first
    db.execute(
        "INSERT INTO events (id, city, data, start_at, category, first_seen, updated_at) VALUES (?,?,?,?,?,?,?)",
        (eid, "testville", "{}", "x", "c", "2026-01-01T00:00:00+00:00", "x"),
    )
    for m in (a, b):
        db.execute("INSERT INTO event_members VALUES (?,?,?,?,?)", (eid, m.source_id, m.record_id, "testville", 1.0))
    split = assign_ids(db, "testville", [Cluster(members=[a], scores=[1]), Cluster(members=[b], scores=[1])])
    ids = [i for i, _ in split]
    assert len(set(ids)) == 2 and eid in ids
