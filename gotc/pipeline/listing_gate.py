"""The "is this a real public event?" gate (ADR-0010).

Every listing from every source passes through :meth:`ListingGate.evaluate` at build time, before clustering,
geocoding or enrichment. Rules live in ``config/listing_gate.yaml``: plain regexes grouped by family (academic
calendar, closure, office hours, appointment, admin deadline, governance meeting, internal only, placeholder, and
campus-only rules). A listing a rule rejects is quarantined with the rule id and a human reason — never silently
dropped — and counted per source in HEALTH.md.

Soft rules can be rescued by ``unless`` patterns or by the listing's category family (a league's registration
deadline is real). Hard rules can only be overridden per source (``listing_gate.keep`` in that source's params).
The gate is pure and deterministic: same listing + same config → same verdict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from gotc.schema import CategoryBasis, SourceEvent
from gotc.settings import CONFIG_DIR

_FLAGS = re.IGNORECASE


@dataclass(frozen=True)
class Rule:
    id: str
    family: str
    reason: str
    hard: bool = False
    scope: str = "any"  # "any" | "institution"
    title: tuple[re.Pattern[str], ...] = ()
    text: tuple[re.Pattern[str], ...] = ()
    labels: tuple[re.Pattern[str], ...] = ()
    labels_none: tuple[re.Pattern[str], ...] = ()  # …and none of the source's labels match these
    unless: tuple[re.Pattern[str], ...] = ()
    basis: tuple[str, ...] = ()


@dataclass(frozen=True)
class Verdict:
    keep: bool
    rule: str | None = None
    family: str | None = None
    reason: str = ""
    evidence: str | None = None  # the text the rule matched
    rescued_by: str | None = None  # a soft rule matched, but this kept it


KEEP = Verdict(True)


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = s.replace("’", "'").replace("‘", "'").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def _compile(pats: Any) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, _FLAGS) for p in (pats or []))


@dataclass
class ListingGate:
    rules: tuple[Rule, ...]
    unless_families: tuple[str, ...] = ()
    unless_categories: tuple[str, ...] = ()
    _source_cache: dict[tuple[str, str], tuple[set[str], tuple[re.Pattern[str], ...], tuple[Rule, ...], bool]] = field(
        default_factory=dict, repr=False
    )

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> ListingGate:
        data = yaml.safe_load((path or CONFIG_DIR / "listing_gate.yaml").read_text())
        rules: list[Rule] = []
        seen: set[str] = set()
        for r in data.get("rules") or []:
            if r["id"] in seen:
                raise ValueError(f"listing gate: duplicate rule id {r['id']!r}")
            seen.add(r["id"])
            rule = Rule(
                id=r["id"],
                family=r["family"],
                reason=r["reason"],
                hard=bool(r.get("hard", False)),
                scope=r.get("scope", "any"),
                title=_compile(r.get("title")),
                text=_compile(r.get("text")),
                labels=_compile(r.get("labels")),
                labels_none=_compile(r.get("labels_none")),
                unless=_compile(r.get("unless")),
                basis=tuple(r.get("basis") or ()),
            )
            if not (rule.title or rule.text or rule.labels or rule.basis):
                raise ValueError(f"listing gate: rule {rule.id} matches nothing")
            if rule.scope not in ("any", "institution"):
                raise ValueError(f"listing gate: rule {rule.id} has unknown scope {rule.scope!r}")
            rules.append(rule)
        return cls(
            rules=tuple(rules),
            unless_families=tuple(data.get("unless_families") or ()),
            unless_categories=tuple(data.get("unless_categories") or ()),
        )

    @property
    def rule_ids(self) -> set[str]:
        return {r.id for r in self.rules}

    def _for_source(
        self, source_id: str, params: dict[str, Any]
    ) -> tuple[set[str], tuple[re.Pattern[str], ...], tuple[Rule, ...], bool]:
        """(rules turned off, keep patterns, extra reject rules, institution scope) for one source."""
        cfg = params.get("listing_gate") or {}
        key = (source_id, repr((sorted(cfg.items()) if isinstance(cfg, dict) else cfg, params.get("audience_filter"))))
        if key in self._source_cache:
            return self._source_cache[key]
        off = set(cfg.get("off") or ())
        unknown = off - self.rule_ids
        if unknown:
            raise ValueError(f"listing gate: {source_id} turns off unknown rules {sorted(unknown)}")
        keep = _compile(cfg.get("keep"))
        extra = tuple(
            Rule(
                id=f"{source_id}:{x['id']}",
                family=x.get("family", "source_rule"),
                reason=x["reason"],
                hard=True,
                title=_compile([x["pattern"]]),
            )
            for x in cfg.get("reject") or ()
        )
        institution = bool(cfg.get("institution", params.get("audience_filter") == "institution"))
        out = (off, keep, extra, institution)
        self._source_cache[key] = out
        return out

    def evaluate(self, ev: SourceEvent, params: dict[str, Any] | None = None, data_type: str | None = None) -> Verdict:
        """Keep or quarantine one listing. ``data_type`` is the source's data type (a volunteer or league source's
        listings are things you sign up for, so their soft-rule matches — "registration deadline" — are rescued)."""
        params = params or {}
        off, keep, extra, institution = self._for_source(ev.source_id, params)
        title = _norm(ev.title)
        text = f"{title}. {_norm(ev.description)[:2000]}"
        if any(p.search(title) for p in keep):
            return KEEP
        family = ev.category.split(".", 1)[0]
        # a category may only rescue a listing when the source said it (or a person checked it): our own guess
        # ("Recruitment Committee Meetings" → a race) mustn't talk the gate out of a rule
        trusted = ev.category_basis in (CategoryBasis.SOURCE_LABEL, CategoryBasis.CURATED) or data_type in (
            "volunteer",
            "leagues",
        )
        rescued_by: str | None = None
        ordered = (*extra, *(r for r in self.rules if r.hard), *(r for r in self.rules if not r.hard))
        for rule in ordered:
            if rule.id in off or (rule.scope == "institution" and not institution):
                continue
            evidence = self._match(rule, ev, title, text)
            if evidence is None:
                continue
            if not rule.hard:
                if trusted and (family in self.unless_families or ev.category in self.unless_categories):
                    rescued_by = rescued_by or f"{rule.id}: category {ev.category}"
                    continue
                hit = next((p for p in rule.unless if p.search(title)), None)
                if hit is not None:
                    rescued_by = rescued_by or f"{rule.id}: {hit.pattern[:60]}"
                    continue
            return Verdict(False, rule.id, rule.family, rule.reason, evidence[:200])
        return Verdict(True, rescued_by=rescued_by)

    @staticmethod
    def _match(rule: Rule, ev: SourceEvent, title: str, text: str) -> str | None:
        labels = [_norm(x) for x in ev.source_categories]
        if rule.labels_none and any(p.search(x) for p in rule.labels_none for x in labels):
            return None  # e.g. the source also tags it "General Public"
        if rule.basis:
            basis = ev.category_basis.value if ev.category_basis else None
            if basis not in rule.basis:
                return None
            if not (rule.title or rule.text or rule.labels):
                return f"category basis {basis}"
        for p in rule.title:
            if m := p.search(title):
                return m.group(0)
        for p in rule.text:
            if m := p.search(text):
                return m.group(0)
        for p in rule.labels:
            for label in labels:
                if p.search(label):
                    return f"label {label!r}"
        return None


@cache
def listing_gate() -> ListingGate:
    return ListingGate.from_yaml()
