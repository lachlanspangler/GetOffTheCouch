"""The real-public-event gate (ADR-0010). Every title here is a real listing from our feeds (2026-10/11 audit),
except the handful marked (synthetic) that pin down an edge case the prompt called out."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from gotc.pipeline.listing_gate import ListingGate, listing_gate
from gotc.schema import CategoryBasis, SourceEvent

NOW = datetime(2026, 11, 2, 18, tzinfo=UTC)
GATE = listing_gate()
CAMPUS = {"audience_filter": "institution"}


def ev(
    title: str,
    category: str = "other.uncategorized",
    *,
    desc: str | None = None,
    labels: list[str] | None = None,
    basis: str | None = None,
    source: str = "src",
) -> SourceEvent:
    return SourceEvent.model_validate(
        {
            "source_id": source,
            "record_id": title[:40],
            "city": "miami",
            "title": title,
            "description": desc,
            "category": category,
            "category_basis": basis or ("fallback" if category == "other.uncategorized" else "classified"),
            "source_categories": labels or [],
            "start": NOW,
            "timezone": "America/New_York",
            "fetched_at": NOW,
        }
    )


def verdict(title: str, params: dict | None = None, data_type: str | None = None, **kw):
    return GATE.evaluate(ev(title, **kw), params or {}, data_type)


# ── rejected, with the rule that should catch each ──
REJECT = [
    # academic calendars
    ("Fall B: Last day to withdraw from the University with a 25% refund of tuition", "academic_calendar"),
    ("Fall C: Last day to withdraw from the University with a WI grade", "academic_calendar"),
    ("Last day to drop classes with a full refund", "academic_calendar"),
    ("Add/Drop period ends", "academic_calendar"),
    ("Final grades due at noon", "academic_calendar"),
    ("Final Exams Begin", "academic_calendar"),
    ("Classes Begin", "academic_calendar"),
    ("First Day of Classes", "academic_calendar"),
    ("Thanksgiving Break", "academic_calendar"),
    ("Priority Registration for Spring 2027", "academic_calendar"),
    ("Tuition payment deadline", "academic_calendar"),
    ("Autumn Quarter: Democracy Day: day of civic service (no classes)", "academic_calendar"),
    # closures
    ("Closed for Thanksgiving", "closure"),
    ("Holiday Closure - Election Day", "closure"),
    ("CLOSED – CHRISTMAS, hope its fabulous", "closure"),
    ("THANKSGIVING – CLOSED come back tomorrow", "closure"),
    ("CLOSED FOR MAINTENANCE", "closure"),
    ("Closed for a Private Event", "closure"),
    ("Halloween – Closed for the Holiday", "closure"),
    ("club closed", "closure"),
    ("All Branches Closed - Veterans Day", "closure"),
    # office hours
    ("Teen Librarian Office Hours", "office_hours"),
    ("King County Department of Local Services Office Hours", "office_hours"),
    ("Office Hours with Department of Neighborhoods", "office_hours"),
    ("Baker Artist Office Hours | NOV 2026", "office_hours"),
    # appointments
    ("Digital Skills: One-On-One Tech Help for Seniors", "appointment"),
    ("1-on-1 Business Advising with CEDF -", "appointment"),
    ("In-person Medicare 1:1 Counseling (Appointment Only)", "appointment"),
    ("Tech Help (By Appointment)", "appointment"),
    # admin deadlines
    ("Scholarship application deadline", "admin_deadline"),
    ("FAFSA priority deadline", "admin_deadline"),
    ("Call for Artists: 2027 Mural Program", "admin_deadline"),
    # governance
    ("Board of Trustees", "governance_meeting"),
    ("Library Board Meeting", "governance_meeting"),
    ("Pioneer Square Preservation Board Meeting", "governance_meeting"),
    ("Citizens' Bond Oversight Committee - Regular - 11-16-26", "governance_meeting"),
    ("Committee Meeting", "governance_meeting"),
    # internal / private / placeholders
    ("Private Event", "internal_only"),
    ("Staff Meeting", "internal_only"),
    ("Holiday Party (invitation only)", "internal_only"),
    ("TBA", "placeholder"),
    ("Hold", "placeholder"),
]


@pytest.mark.parametrize(("title", "rule"), REJECT)
def test_non_events_are_held_back_with_the_right_rule(title, rule):
    v = verdict(title)
    assert not v.keep and v.rule == rule, (title, v)
    assert v.reason and v.family and v.evidence


CAMPUS_REJECT = [
    ("Concrete Canoe Hull Design Meeting", "campus_meeting"),
    ("Regular Meeting", "governance_meeting"),
    ("Campus Visit (Info Session + Campus Tour)", "campus_admissions"),
    ("Inside the Robinson Executive MBA: Virtual Information Session", "campus_admissions"),
    ("Trojan Talk with McMaster-Carr", "campus_career"),
    ("FIU BBC All Majors Career Expo (Fall 2026)", "campus_career"),
    ('Friday Fellows: "Ask the IRB: All of Your Burning Questions Answered"', "campus_academic_admin"),
    ("Laboratory Medicine Grand Rounds: Design of Smart Medicines", "campus_academic_admin"),
    ("SJSU Official Syllabus Workshop", "campus_academic_admin"),
]


@pytest.mark.parametrize(("title", "rule"), CAMPUS_REJECT)
def test_campus_feeds_get_the_stricter_rules(title, rule):
    v = verdict(title, CAMPUS)
    assert not v.keep and v.rule == rule, (title, v)


def test_campus_rules_never_touch_ordinary_sources():
    for title, rule in CAMPUS_REJECT:
        if rule.startswith("campus_"):
            assert verdict(title).rule != rule


def test_description_says_students_only():
    v = verdict("What's My Story and How Can I Tell It?", CAMPUS, desc="This event is open to all students.")
    assert not v.keep and v.rule == "internal_only"
    v = verdict(
        "TechLab Laser Cutting Workshop", CAMPUS, desc="This event is open to all members.", category="arts.workshop"
    )
    assert v.keep  # library/makerspace "members" includes the public
    v = verdict("Lecture", CAMPUS, desc="This lecture is open to students and the public.", category="learning.talk")
    assert v.keep


# ── real events that use the same words: must be kept ──
KEEP = [
    # the prompt's own examples
    ("Registration Deadline: Spring Kickball League", "sports_league.kickball"),
    ("Last day to register for the Turkey Trot 5K", "fitness.race"),
    ("Volunteer registration closes for Race Day", "volunteer.one_off"),
    ("Open House at the Central Library", "other.uncategorized"),
    ("Free Lecture: The History of Miami Beach", "learning.talk"),
    # "holiday", "closed", "board" in real events
    ("Holiday Pops", "music.classical"),
    ('Tim Brey Trio - "Snowed In" Holiday Album Release', "music.concert"),
    ("Holiday Teen Basketball Jam at Ellis", "sports_league.basketball"),
    ("White Christmas presented with Open Movie Captions – Holiday Film Series", "arts.film"),
    ("Closed Captioned Screening: Wicked", "arts.film"),
    ("Closing Reception: Recent Work by Curtis Ross", "arts.gallery"),
    ("Board Game Meetup", "trivia_games.board_games"),
    ("Card & Board Games", "trivia_games.board_games"),
    ("Brunch & Board Games", "trivia_games.board_games"),
    ("Friends of the Library Board Book Sale", "community.market"),
    ("Teen Library Advisory Committee", "family.teens"),
    # public civic meetings a newcomer can go to
    ("Shannon Park Community Meeting (CMPD North Tryon Division)", "community.neighborhood"),
    ("Main Library Interior Redesign | Public Input Session", "community.neighborhood"),
    ("City Council District 41: Monthly Gardener Gatherings", "outdoors.garden"),
    ("City Council Candidate Forum", "community.neighborhood"),
    # games against a placeholder opponent still happen
    ("Hawks vs TBD", "sports_watch.game"),
    ("University of Central Oklahoma Women's Soccer vs TBD - Quarterfinals", "sports_watch.game"),
    ("Sacramento State Men's Basketball vs Jessup - Faculty and Staff Appreciation Night", "sports_watch.game"),
    # program words that aren't appointments or deadlines
    ("Information Session for Adult English Learners", "learning.language"),
    ("Kids' No School Day Camp", "family.kids"),
    ("New Volunteer Orientation", "volunteer.one_off"),
    ("xTool Laser Cutter and Engraver Orientation", "arts.workshop"),
    ("Main Cinema Staff Picks: Possession", "arts.film"),
    ("Member Preview: Monet in Bloom", "arts.museum"),
    ("Call for vendors: Holiday Craft Fair", "community.market"),
]


@pytest.mark.parametrize(("title", "category"), KEEP)
def test_real_events_with_the_same_words_are_kept(title, category):
    v = verdict(title, category=category, basis="source_label" if category != "other.uncategorized" else None)
    assert v.keep, (title, v)


def test_a_league_signup_deadline_survives_even_on_a_campus_feed():
    v = verdict(
        "Intramural Flag Football League: Registration Deadline", CAMPUS, category="sports_league.flag_football"
    )
    assert v.keep


def test_a_guessed_category_cannot_rescue_a_soft_rule():
    # our classifier guessed "a race" for a committee meeting; only a source label or a person may rescue
    guessed = ev("Recruitment Committee Meetings", category="fitness.race", basis="classified")
    assert not GATE.evaluate(guessed, {}).keep
    assert GATE.evaluate(guessed, {}, data_type="volunteer").keep  # a volunteer source's listings are signups


def test_the_fiu_withdrawal_deadline_is_gone_even_from_a_mixed_calendar():
    labels = ["Students", "Faculty & Staff", "Prospective Students", "Academic Calendar", "fall", "Fall B"]
    e = ev(
        "Fall B: Last day to withdraw from the University with a 25% refund of tuition",
        labels=labels,
        source="fiu_events",
    )
    v = GATE.evaluate(e, CAMPUS)
    assert not v.keep and v.family == "academic_calendar"


# ── per-source overrides ──
def test_per_source_overrides_tighten_and_loosen():
    gate = ListingGate.from_yaml()
    params = {
        "listing_gate": {
            "off": ["governance_meeting"],
            "keep": [r"\bClosed for Private Event\b"],
            "reject": [{"id": "no_tours", "pattern": r"\btour\b", "reason": "members-only tours"}],
        }
    }
    assert gate.evaluate(ev("Library Board Meeting", source="a"), params).keep  # rule off
    assert gate.evaluate(ev("Closed for Private Event", source="a"), params).keep  # keep beats a hard rule
    v = gate.evaluate(ev("Garden tour", category="outdoors.garden", source="a"), params)
    assert not v.keep and v.rule == "a:no_tours" and v.reason == "members-only tours"
    # institution scope can be switched on for a feed that isn't flagged audience_filter
    assert not gate.evaluate(
        ev("Trojan Talk with McMaster-Carr", source="b"), {"listing_gate": {"institution": True}}
    ).keep


def test_unknown_rule_ids_in_overrides_fail_loudly():
    gate = ListingGate.from_yaml()
    with pytest.raises(ValueError, match="unknown rules"):
        gate.evaluate(ev("x y", source="c"), {"listing_gate": {"off": ["no_such_rule"]}})


def test_rules_file_is_well_formed(tmp_path: Path):
    bad = tmp_path / "g.yaml"
    bad.write_text(
        "version: 1\nrules:\n  - {id: a, family: f, reason: r, title: ['x']}\n  - {id: a, family: f, reason: r, title: ['y']}\n"
    )
    with pytest.raises(ValueError, match="duplicate"):
        ListingGate.from_yaml(bad)
    bad.write_text("version: 1\nrules:\n  - {id: a, family: f, reason: r}\n")
    with pytest.raises(ValueError, match="matches nothing"):
        ListingGate.from_yaml(bad)


def test_every_rule_has_a_reason_a_person_can_read():
    for r in GATE.rules:
        assert len(r.reason) >= 20 and not r.reason.endswith("."), r.id


def test_uncategorized_campus_listings_are_published_not_held():
    # campus_uncategorized was retired after the cold data review (about 55% of what it held were real talks and
    # exhibitions): an uncategorized campus listing publishes as uncategorized, with no estimates
    for title in ["Adraint Bereal: As It Appears", "Fortlandia", "Roar Lounge"]:
        assert GATE.evaluate(ev(title, basis=CategoryBasis.FALLBACK.value), CAMPUS).keep


# ── data review 2026-11-02: misses and false positives, pinned ──
REVIEW_REJECT = [
    ("1:1 Tech Mentor Appointment", "appointment", {}),
    ("Tutores de Tecnología: Sesión de apoyo 1 a 1", "appointment", {}),
    ("Pearson Test Center testing", "proctored_testing", {}),
    ("GED Testing", "proctored_testing", {}),
    ("ESL Pre-test Session", "proctored_testing", {}),
    ("Closed in Observance of Thanksgiving Holiday", "closure", {}),
    ("SLPL Closed", "closure", {}),
    ("Bar is Closed", "closure", {}),
    ("Nassau Summer/Fall Street Closures", "closure", {}),
    ("Community Surveillance Working Group Meeting", "governance_meeting", {}),
    ("APO Eboard + Chapter + Pledge Class", "campus_meeting", CAMPUS),
    ('"Shy Longhorns Society" SHARE Community Meeting', "campus_support_group", CAMPUS),
    ("Christian Faculty and Staff Network hosts UT Women's Prayer Group", "campus_meeting", CAMPUS),
]


@pytest.mark.parametrize(("title", "rule", "params"), REVIEW_REJECT)
def test_data_review_misses_are_caught(title, rule, params):
    v = verdict(title, params)
    assert not v.keep and v.rule == rule, (title, v)


def test_ticketed_shows_are_not_calendar_notices():
    for title in ["Cam Kirk Studios: Night School Final Exam", "2027 Unrivaled Season 1 on 1",
                  "Koffin Kats w/ Voodoo Glow Skulls & the Board of Directors"]:  # fmt: skip
        assert verdict(title, {}, "ticket_prices").keep, title


def test_board_games_program_and_campus_holiday_concert_wording():
    assert verdict('The "Board" Meeting', category="trivia_games.board_games", basis="source_label").keep
    assert (
        verdict("Heinz Chapel Choir Campus Holiday Concert", category="music.classical", basis="source_label").rule
        != "closure"
    )


def test_campus_audience_rule_reads_the_description_and_ignores_a_bare_students_tag():
    # a lecture whose title doesn't say "lecture"
    e = ev("A Rift in Time. Reinhart Koselleck and the Theory of History", labels=["Faculty & Staff"],
           desc="A lecture by Prof. X on historical time.")  # fmt: skip
    assert GATE.evaluate(e, CAMPUS).keep
    # campuses tag public events "Students" too
    assert GATE.evaluate(ev("Forbidden Pages: Past and Present", labels=["Students"]), CAMPUS).keep
    # still held: tagged only for staff, no rescue
    assert not GATE.evaluate(ev("Canvas: Elements of Teaching - Modules", labels=["Faculty & Staff"]), CAMPUS).keep


def test_code_review_ticketed_and_venue_false_positives():
    for title, dt in [
        ("Office Hours: Live Comedy Podcast", "ticket_prices"),
        ("Final Exam Trivia Night", "concerts"),
        ("First Day of School Bash", None),
        ("Reading Day at the Park", None),
        ("Holiday Hours Market", None),
        ("Case Closed", "concerts"),
        ("Street Closure Block Party", None),
        ("Private Party Night at Club Space", "ticket_prices"),
    ]:
        assert verdict(title, {}, dt).keep, title
    assert not verdict("Closed for a Private Event", {}, "concerts").keep  # venue calendars still post closures
    assert not verdict("Private Event", {}, "concerts").keep  # placeholder
