from gotc.pipeline.normalize import links_from_html, location_from_text, normalize_record


def test_links_by_host_and_anchor_text():
    html = (
        '<p><a href="https://www.signupgenius.com/go/abc">here</a> or '
        '<a href="https://example.org/register">Register now</a> and '
        '<a href="https://example.org/about">About us</a> '
        "also https://www.eventbrite.com/e/123 in plain text</p>"
    )
    kinds = {(k, u) for k, u, _ in links_from_html(html)}
    assert ("registration", "https://www.signupgenius.com/go/abc") in kinds
    assert ("registration", "https://example.org/register") in kinds
    assert ("rsvp", "https://www.eventbrite.com/e/123") in kinds
    assert not any("about" in u for _, u in kinds)


def test_location_lines():
    assert (
        location_from_text("Dates: Sundays\nLocation: Minnehaha Regional Park. Sign up below.")
        == "Minnehaha Regional Park"
    )
    assert location_from_text("Meet at: the north lot") == "the north lot"
    assert location_from_text("no location here") is None


def test_volunteer_free_and_availability():
    rec = {"source_id": "s", "fetched_at": "x", "category": "volunteer.one_off", "price": {}, "availability": "unknown"}
    out = normalize_record(rec, "S")
    assert out["price"]["is_free"] and out["availability"] == "free_no_ticket"


def test_paid_volunteer_is_not_marked_free():
    rec = {"source_id": "s", "fetched_at": "x", "category": "volunteer.one_off", "price": {"min": 25}}
    assert not normalize_record(rec, "S")["price"].get("is_free")


def test_says_free():
    from gotc.adapters.common import says_free

    assert says_free("Free pub quiz, teams up to 6")
    assert says_free("Trivia", "Admission is free.")
    assert says_free("No cover!")
    assert not says_free("Gluten free brunch")
    assert not says_free("Free parking available. Tickets $25")
    assert not says_free("Free drinks for the first 50 guests")


def test_cancelled_titles_set_availability():
    out = normalize_record(
        {
            "source_id": "s",
            "fetched_at": "x",
            "title": "CANCELED: SoUP Research Presentation",
            "category": "learning.tech",
        },
        "S",
    )
    assert out["availability"] == "cancelled"
    out = normalize_record(
        {"source_id": "s", "fetched_at": "x", "title": "[Postponed] Jazz Night", "category": "music.concert"}, "S"
    )
    assert out["availability"] == "postponed"


def test_institution_audience_filter_is_opt_in():
    from gotc.pipeline.normalize import audience_skip

    internal = {"title": "NYU Faculty Housing Pet Photo Contest"}
    public = {"title": "Free Jazz Concert on the Quad", "description": "Open to the public."}
    assert audience_skip(internal, "institution")
    assert audience_skip({"title": "Dissertation Defense: J. Doe"}, "institution")
    assert audience_skip({"title": "Talk", "description": "For current graduate students only"}, "institution")
    assert audience_skip(public, "institution") is None
    assert audience_skip(internal, None) is None


def test_online_only_events_are_skipped_globally():
    from gotc.pipeline.normalize import location_skip

    assert location_skip({"location": {"venue_name": "Virtual"}}, None)
    assert location_skip({"location": {"address": "Online via Zoom"}}, None)
    assert location_skip({"title": "Resume Workshop (Virtual)", "location": {}}, None)
    assert location_skip({"title": "Trivia", "location": {"venue_name": "Virtue Cider"}}, None) is None
    assert location_skip(
        {"title": "Game", "location": {"venue_name": "Norman, Okla., Tennis Center"}}, r"\b(Okla)\b\.?"
    )


def test_fix_category_for_arena_feeds():
    from gotc.pipeline.normalize import fix_category

    def cat(title, c="music.concert"):
        r = {"title": title, "category": c}
        fix_category(r)
        return r["category"]

    assert cat("Detroit Pistons vs Miami HEAT") == "sports_watch.game"
    assert cat("America Business Forum") == "learning.networking"
    assert cat("Kaseya Center All-Access Tour") == "other.uncategorized"
    assert cat("Nick Cannon Presents: Wild ‘N Out Live") == "nightlife.comedy"
    assert cat("Monster Jam") == "sports_watch.game"
    assert cat("Doja Cat") == "music.concert"
    assert cat("Kickball: Team A vs Team B", "sports_league.kickball") == "sports_league.kickball"
