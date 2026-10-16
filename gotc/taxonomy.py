"""Category taxonomy: load config/taxonomy.yaml, validate ids, classify free text.

Classification is deliberately simple and explainable: keyword phrases with word boundaries,
longest (most specific) phrase wins, child categories beat parents. Every classification
returns the matched phrase so the provenance shows *why* something is "Trivia".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from gotc.settings import CONFIG_DIR

FALLBACK = "other.uncategorized"


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    parent: str | None
    social: float
    attendance: tuple[float, float, float]
    icon: str
    match: tuple[str, ...] = ()
    deprecated: str | None = None


@dataclass(frozen=True)
class Classification:
    category: str
    confidence: float
    matched: str | None


@dataclass
class Taxonomy:
    version: int
    categories: dict[str, Category]
    tags: dict[str, str]
    _patterns: list[tuple[re.Pattern[str], str, str]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        pats: list[tuple[re.Pattern[str], str, str]] = []
        for cat in self.categories.values():
            for phrase in cat.match:
                p = phrase.strip().lower()
                if p:
                    pats.append((re.compile(rf"(?<![\w]){re.escape(p)}(?![\w])"), cat.id, p))
        # most specific first: longer phrases, then child categories
        pats.sort(key=lambda t: (-len(t[2]), -t[1].count(".")))
        self._patterns = pats

    def resolve(self, cat_id: str) -> str:
        """Return the live id for ``cat_id`` (follows deprecations). Raises KeyError if unknown."""
        seen: set[str] = set()
        while True:
            cat = self.categories[cat_id]
            if not cat.deprecated:
                return cat.id
            if cat_id in seen:
                raise ValueError(f"deprecation cycle at {cat_id}")
            seen.add(cat_id)
            cat_id = cat.deprecated

    def is_valid(self, cat_id: str) -> bool:
        return cat_id in self.categories

    def top(self, cat_id: str) -> str:
        return cat_id.split(".", 1)[0]

    def classify(self, *texts: str | None, default: str = FALLBACK) -> Classification:
        """Classify free text. Title should be passed first: matches in earlier texts win ties."""
        best: tuple[int, int, int, str, str] | None = None  # (text_rank, -len, -depth, id, phrase)
        for rank, text in enumerate(t for t in texts if t):
            hay = " " + re.sub(r"\s+", " ", text.lower()) + " "
            for pat, cat_id, phrase in self._patterns:
                if pat.search(hay):
                    key = (rank, -len(phrase), -cat_id.count("."), cat_id, phrase)
                    if best is None or key < best:
                        best = key
                    break  # patterns are sorted by specificity; first hit in this text is its best
        if best is None:
            return Classification(default, 0.2, None)
        rank, _, _, cat_id, phrase = best
        conf = 0.75 if rank == 0 else 0.55
        if len(phrase) >= 10:
            conf += 0.1
        return Classification(cat_id, min(conf, 0.9), phrase)

    def valid_tags(self, tags: list[str]) -> list[str]:
        return sorted({t for t in tags if t in self.tags})


def _walk(node: dict[str, Any], parent: Category | None, prefix: str, out: dict[str, Category]) -> None:
    for key, spec in node.items():
        spec = spec or {}
        cid = f"{prefix}.{key}" if prefix else key
        att = spec.get("attendance") or (parent.attendance if parent else (20, 100, 1000))
        cat = Category(
            id=cid,
            label=spec.get("label", key.replace("_", " ").title()),
            parent=parent.id if parent else None,
            social=float(spec.get("social", parent.social if parent else 0.4)),
            attendance=(float(att[0]), float(att[1]), float(att[2])),
            icon=spec.get("icon", parent.icon if parent else "dot"),
            match=tuple(spec.get("match") or ()),
            deprecated=spec.get("deprecated"),
        )
        if not (cat.attendance[0] <= cat.attendance[1] <= cat.attendance[2]):
            raise ValueError(f"{cid}: attendance prior must be ordered p10 <= p50 <= p90")
        out[cid] = cat
        _walk(spec.get("children") or {}, cat, cid, out)


def load_taxonomy(path: Path | None = None) -> Taxonomy:
    data = yaml.safe_load((path or CONFIG_DIR / "taxonomy.yaml").read_text())
    cats: dict[str, Category] = {}
    _walk(data["categories"], None, "", cats)
    if FALLBACK not in cats:
        raise ValueError(f"taxonomy must define {FALLBACK}")
    for c in cats.values():
        if c.deprecated and c.deprecated not in cats:
            raise ValueError(f"{c.id} deprecated to unknown id {c.deprecated}")
    return Taxonomy(version=int(data["version"]), categories=cats, tags=dict(data.get("tags") or {}))


@cache
def taxonomy() -> Taxonomy:
    return load_taxonomy()
