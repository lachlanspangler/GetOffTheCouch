import pytest

from gotc.taxonomy import FALLBACK, load_taxonomy, taxonomy


def test_taxonomy_loads_and_has_fallback():
    t = taxonomy()
    assert FALLBACK in t.categories
    assert "sports_league.kickball" in t.categories
    assert t.categories["sports_league.kickball"].parent == "sports_league"


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Tuesday Trivia at the Pub", "trivia_games.trivia"),
        ("Fall Kickball League — Registration", "sports_league.kickball"),
        ("Lake Harriet Buckthorn Removal Volunteer Day", "volunteer.one_off"),
        ("Minnesota Renaissance Festival", "niche.ren_faire"),
        ("Anime Detour 2027", "niche.anime_con"),
        ("Saturday Morning Run Club", "fitness.run_club"),
        ("Grand Opening Party at the new taproom", "nightlife.opening"),
        ("Linden Hills Farmers Market", "community.market"),
        ("Cars and Coffee Twin Cities", "niche.car_show"),
    ],
)
def test_classify(title, expected):
    assert taxonomy().classify(title).category == expected


def test_classify_prefers_longer_phrase_and_reports_match():
    c = taxonomy().classify("Twin Cities Music Festival")
    assert c.category == "music.festival"
    assert c.matched == "music festival"


def test_classify_falls_back_with_low_confidence():
    c = taxonomy().classify("Xyzzy")
    assert c.category == FALLBACK and c.confidence < 0.5


def test_title_beats_description():
    c = taxonomy().classify("Trivia Night", "after trivia there's karaoke")
    assert c.category == "trivia_games.trivia"


def test_deprecation_resolves(tmp_path):
    p = tmp_path / "t.yaml"
    p.write_text(
        "version: 1\ncategories:\n  a:\n    label: A\n    children:\n      old: {deprecated: a.new}\n      new: {}\n"
        "  other:\n    children:\n      uncategorized: {}\n"
    )
    t = load_taxonomy(p)
    assert t.resolve("a.old") == "a.new"


def test_bad_attendance_prior_rejected(tmp_path):
    p = tmp_path / "t.yaml"
    p.write_text("version: 1\ncategories:\n  a: {attendance: [10, 5, 20]}\n  other: {children: {uncategorized: {}}}\n")
    with pytest.raises(ValueError, match="ordered"):
        load_taxonomy(p)
