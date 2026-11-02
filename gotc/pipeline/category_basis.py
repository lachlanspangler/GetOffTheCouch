"""Where did a listing's category come from? (honest provenance, ADR-0010)

A category is only "reported by the source" when the source's own label produced it. Everything else is ours:
the keyword classifier (derived), a config default for a single-kind source (defaulted), or nothing at all
(uncategorized, defaulted). Adapters that know set ``category_basis`` themselves (``gotc.adapters.common.categorize``);
for the rest, and for records stored before schema 1.8, :func:`infer_basis` works it out from the record and the
source's config. It errs toward *not* claiming the source said so.
"""

from __future__ import annotations

import re
from typing import Any

from gotc.schema import CategoryBasis, Method, SourceEvent
from gotc.taxonomy import FALLBACK, Taxonomy

#: Adapters whose categories come from a typed field in the source data (a sport, a race type, an event type)
#: or a hand-verified registry. Their category is never a config guess.
_ADAPTER_BASIS: dict[str, CategoryBasis] = {
    "curated": CategoryBasis.CURATED,
    "volo": CategoryBasis.SOURCE_LABEL,
    "runsignup": CategoryBasis.SOURCE_LABEL,
    "makerfaire": CategoryBasis.SOURCE_KIND,
    "teamtrivia": CategoryBasis.SOURCE_KIND,
    "challenge": CategoryBasis.SOURCE_KIND,
    "upcomingcons": CategoryBasis.SOURCE_KIND,
    "demo": CategoryBasis.SOURCE_LABEL,
}

#: Fields an adapter may fill from config instead of the source: (field, param keys that supply it).
CONFIG_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("organizer", ("organizer",)),
    ("venue", ("venue_label", "venue_name")),
)


def infer_basis(
    ev: SourceEvent, params: dict[str, Any], tax: Taxonomy, adapter: str | None = None
) -> tuple[CategoryBasis, str]:
    """(basis, note) for a record whose adapter didn't say. Deterministic; prefers the least flattering answer."""
    cat = ev.category
    if cat == FALLBACK:
        return CategoryBasis.FALLBACK, "no category in the listing"
    cmap: dict[str, str] = params.get("category_map") or {}
    for label in ev.source_categories:
        mapped = cmap.get(label)
        if mapped and _same(tax, mapped, cat):
            return CategoryBasis.SOURCE_LABEL, f"source label {label!r}"
    hit = tax.classify(ev.title, " ".join(ev.source_categories), ev.description, default=FALLBACK)
    if hit.matched and _same(tax, hit.category, cat):
        return CategoryBasis.CLASSIFIED, f"keyword {hit.matched!r}"
    default = params.get("default_category")
    if default and _same(tax, default, cat):
        return CategoryBasis.SOURCE_KIND, "this source's default category (our config)"
    if adapter in _ADAPTER_BASIS:
        basis = _ADAPTER_BASIS[adapter]
        return basis, {
            CategoryBasis.SOURCE_LABEL: "the source's own event type",
            CategoryBasis.SOURCE_KIND: "this source only lists one kind of event",
            CategoryBasis.CURATED: "checked by hand",
        }.get(basis, "")
    if ev.source_categories:
        # a typed label we map in code (e.g. a ticketing segment) or a title rule (e.g. "A vs B" → a game)
        return CategoryBasis.CLASSIFIED, UNEXPLAINED[0]
    return CategoryBasis.CLASSIFIED, UNEXPLAINED[1]


#: notes infer_basis uses when it can't point at a label, a keyword or a config default
UNEXPLAINED = ("worked out from the source's labels and title", "worked out from the title")


def _same(tax: Taxonomy, a: str, b: str) -> bool:
    try:
        return tax.resolve(a) == tax.resolve(b)
    except KeyError:
        return False


def ensure_basis(ev: SourceEvent, params: dict[str, Any], tax: Taxonomy, adapter: str | None = None) -> None:
    """Fill ``category_basis`` / ``category_note`` / ``defaulted_fields`` in place (idempotent)."""
    if ev.category == FALLBACK:
        ev.category_basis, ev.category_note = CategoryBasis.FALLBACK, ev.category_note or "no category in the listing"
    elif ev.category_basis is None:
        ev.category_basis, ev.category_note = infer_basis(ev, params, tax, adapter)
    found = set(ev.defaulted_fields)
    if ev.category_basis in (CategoryBasis.SOURCE_KIND, CategoryBasis.FALLBACK):
        found.add("category")
    for field, keys in CONFIG_FIELDS:
        configured = {str(params[k]).strip() for k in keys if params.get(k)}
        if field == "venue" and isinstance(params.get("venue"), dict) and params["venue"].get("name"):
            configured.add(str(params["venue"]["name"]).strip())
        value = ev.organizer if field == "organizer" else ev.location.venue_name
        if value and value.strip() in configured:
            found.add(field)
    ev.defaulted_fields = sorted(found)


def category_method(basis: CategoryBasis | None) -> Method:
    """The provenance method a category basis may claim. Only a source label is "reported"."""
    return {
        CategoryBasis.SOURCE_LABEL: Method.REPORTED,
        CategoryBasis.CLASSIFIED: Method.DERIVED,
        CategoryBasis.SOURCE_KIND: Method.DEFAULTED,
        CategoryBasis.FALLBACK: Method.DEFAULTED,
        CategoryBasis.CURATED: Method.CURATED,
    }.get(basis or CategoryBasis.CLASSIFIED, Method.DERIVED)


def is_uncategorized(category: str) -> bool:
    return category == FALLBACK


#: Names/ids/URLs of calendars that list many kinds of things (ADR-0010). Such a source may only set a
#: ``default_category`` with a ``single_kind_reason`` saying why it really is one kind of thing.
MIXED_SOURCE = re.compile(
    r"universit|college|campus|\bschool\b|librar|\bpl\b|county|city of|\bcity\b|government|parks?\b|recreation|"
    r"conservancy|botanical|garden|arboretum|\bzoo\b|museum|visit |tourism|\bcvb\b|downtown|district|partnership|"
    r"chamber|alliance|community center|police|cmpd|neighborhood|historic|cultural|arts center|\bhouse\b|"
    r"events calendar|calendar \(|calendar$|science center|nature center|wildflower|aquarium|taproom|brewing|"
    r"brewery|pearl|triangle|special events|permitted",
    re.IGNORECASE,
)
MIXED_ADAPTERS = frozenset({"bibliocommons", "communico", "simpleview", "localist", "livewhale"})


def looks_mixed(source_id: str, name: str, adapter: str, params: dict[str, Any], homepage: str | None = None) -> bool:
    """True when a source looks like a calendar of many kinds of things (library, campus, city, park, museum…)."""
    if params.get("audience_filter") == "institution" or adapter in MIXED_ADAPTERS:
        return True
    return bool(MIXED_SOURCE.search(f"{name} {source_id} {params.get('base_url', '')} {homepage or ''}"))


def default_violations(sources: list[Any]) -> list[str]:
    """Sources that guess a catch-all category for a mixed calendar (doctor + tests)."""
    bad: list[str] = []
    for s in sources:
        if not s.params.get("default_category") or s.params.get("single_kind_reason"):
            continue
        if looks_mixed(s.id, s.name, s.adapter, s.params, getattr(s, "homepage", None)):
            bad.append(f"{s.id}: mixed calendar with default_category {s.params['default_category']!r}")
    return bad
