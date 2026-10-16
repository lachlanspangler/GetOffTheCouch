"""Text normalization for entity resolution (titles, venue names) and geo helpers."""

from __future__ import annotations

import math
import re
import unicodedata
from functools import lru_cache

from rapidfuzz import fuzz

_TITLE_NOISE = re.compile(
    r"\b(presents?|live|in concert|tour|tickets?|the|an?|official|show|w/|with special guests?|"
    r"featuring|feat\.?|ft\.?|\d{4}|tour \d{4}|night \d)\b",
    re.I,
)
_VENUE_NOISE = re.compile(
    r"\b(the|theatre|theater|hall|arena|center|centre|ballroom|club|venue|music|amphitheater|amphitheatre|"
    r"auditorium|stadium|field|park|minneapolis|mpls|nyc|new york)\b",
    re.I,
)
_PUNCT = re.compile(r"[^\w\s]")


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().replace("&", " and ")


@lru_cache(maxsize=200_000)
def norm_title(s: str) -> str:
    s = fold(s)
    s = s.split(" | ")[0]
    s = _PUNCT.sub(" ", s)
    s = _TITLE_NOISE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


@lru_cache(maxsize=50_000)
def norm_venue(s: str | None) -> str:
    if not s:
        return ""
    s = _PUNCT.sub(" ", fold(s))
    core = _VENUE_NOISE.sub(" ", s)
    core = re.sub(r"\s+", " ", core).strip()
    return core or re.sub(r"\s+", " ", s).strip()


def title_similarity(a: str, b: str) -> float:
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return 0.0
    return max(fuzz.token_set_ratio(na, nb), fuzz.ratio(na, nb)) / 100.0


def venue_similarity(a: str | None, b: str | None) -> float:
    na, nb = norm_venue(a), norm_venue(b)
    if not na or not nb:
        return 0.0
    return fuzz.token_set_ratio(na, nb) / 100.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
