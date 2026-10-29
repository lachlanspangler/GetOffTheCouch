"""Honest category provenance (ADR-0010): only a source's own label may be called "reported by the source"."""

from __future__ import annotations

from datetime import UTC, datetime

from gotc.adapters.common import categorize
from gotc.pipeline.category_basis import category_method, ensure_basis, infer_basis
from gotc.pipeline.enrich import estimate_attendance, social_score
from gotc.schema import CategoryBasis, Event, EventKind, Location, Method, Price, SourceEvent, SourceRef
from gotc.taxonomy import FALLBACK, taxonomy

NOW = datetime(2026, 10, 29, 12, tzinfo=UTC)
TAX = taxonomy()


def rec(title: str, category: str, labels: list[str] | None = None, **kw: object) -> SourceEvent:
    return SourceEvent.model_validate(
        {
            "source_id": "fiu_events",
            "record_id": "1",
            "city": "miami",
            "title": title,
            "category": category,
            "source_categories": labels or [],
            "start": NOW,
            "timezone": "America/New_York",
            "fetched_at": NOW,
            **kw,
        }
    )


FIU = {"default_category": "learning.networking", "organizer": "Florida International University"}


def test_the_fiu_withdrawal_deadline_is_a_config_default_not_a_reported_category():
    # the real listing: the source's labels were audiences and terms, none of which say "networking"
    labels = ["Students", "Faculty & Staff", "Prospective Students", "Academic Calendar", "fall", "Fall B"]
    r = rec(
        "Fall B: Last day to withdraw from the University with a 25% refund of tuition", "learning.networking", labels
    )
    basis, note = infer_basis(r, FIU, TAX)
    assert basis == CategoryBasis.SOURCE_KIND and "config" in note
    assert category_method(basis) == Method.DEFAULTED


def test_categorize_prefers_the_source_label_then_the_classifier_then_the_default():
    params = {"category_map": {"Concerts": "music.concert"}, "default_category": "learning.networking"}
    by_label = categorize(TAX, params, "Fall recital", ["Concerts"], None)
    assert by_label == {
        "category": "music.concert",
        "category_basis": "source_label",
        "category_note": "source label 'Concerts'",
    }
    by_kw = categorize(TAX, params, "Tuesday Night Trivia", [], None)
    assert by_kw["category_basis"] == "classified" and by_kw["category"].startswith("trivia_games")
    by_default = categorize(TAX, params, "Fall B: Last day to withdraw", ["Academic Calendar"], None)
    assert by_default["category_basis"] == "source_kind" and by_default["category"] == "learning.networking"
    nothing = categorize(TAX, {}, "Fall B: Last day to withdraw", ["Academic Calendar"], None)
    assert nothing == {
        "category": FALLBACK,
        "category_basis": "fallback",
        "category_note": "no category in the listing",
    }


def test_only_a_source_label_maps_to_reported():
    assert category_method(CategoryBasis.SOURCE_LABEL) == Method.REPORTED
    for basis in (CategoryBasis.CLASSIFIED, CategoryBasis.SOURCE_KIND, CategoryBasis.FALLBACK, None):
        assert category_method(basis) != Method.REPORTED
    assert category_method(CategoryBasis.CURATED) == Method.CURATED


def test_infer_basis_recognises_mapped_labels_and_keywords():
    params = {"category_map": {"Music": "music.concert"}}
    assert infer_basis(rec("Band night", "music.concert", ["Music"]), params, TAX)[0] == CategoryBasis.SOURCE_LABEL
    assert infer_basis(rec("Pub trivia night", "trivia_games.trivia"), {}, TAX)[0] == CategoryBasis.CLASSIFIED
    assert infer_basis(rec("Something", FALLBACK), {}, TAX)[0] == CategoryBasis.FALLBACK


def test_ensure_basis_marks_config_filled_fields():
    r = rec(
        "Board meeting",
        "learning.networking",
        organizer="Florida International University",
        location=Location(venue_name="Main Hall"),
    )
    ensure_basis(r, {**FIU, "venue_label": "Main Hall"}, TAX)
    assert set(r.defaulted_fields) == {"category", "organizer", "venue"}


def event(category: str) -> Event:
    return Event(
        id="e1",
        city="miami",
        title="x",
        kind=EventKind.ONE_OFF,
        category=category,
        start=NOW,
        timezone="America/New_York",
        location=Location(),
        price=Price(),
        sources=[SourceRef(source_id="s", record_id="1", fetched_at=NOW)],
        first_seen=NOW,
        last_checked=NOW,
    )


def test_uncategorized_listings_get_no_category_prior_and_no_social_score():
    ev = event(FALLBACK)
    assert estimate_attendance(ev, TAX, None, None, None) is None
    assert social_score(ev, TAX) is None
    # a reported count or a real venue capacity still gives an honest band
    assert estimate_attendance(ev, TAX, None, None, 120) is not None
    assert estimate_attendance(ev, TAX, 500, "venue file", None) is not None
    # a categorized listing keeps its prior
    assert estimate_attendance(event("trivia_games.trivia"), TAX, None, None, None) is not None
