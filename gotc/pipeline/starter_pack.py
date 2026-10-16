"""New-resident starter pack: official state deadlines (license, vehicle, voting) from config/starter_pack/<st>.yaml.

Every item quotes its .gov source verbatim; `verify()` re-checks the quote daily (same evidence check as the
curated registry). The dashboard turns `days_after_move` into personal due dates from the user's move date.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from gotc.adapters.curated import evidence_present
from gotc.http.client import FetchError, PoliteClient
from gotc.schema import StarterItem
from gotc.settings import CONFIG_DIR
from gotc.storage.db import Database, iso, parse_iso

log = logging.getLogger(__name__)
RECHECK = timedelta(hours=24)


def load(state: str, config_dir: Path = CONFIG_DIR) -> list[StarterItem]:
    path = config_dir / "starter_pack" / f"{state.lower()}.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    if data.get("state", "").upper() != state.upper():
        raise ValueError(f"{path.name}: state field must be {state.upper()}")
    return [StarterItem.model_validate(i) for i in data.get("items", [])]


def verify(db: Database, http: PoliteClient | None, items: list[StarterItem], now: datetime) -> int:
    """Re-check stale quotes (≤ once a day per item). Returns the number of pages fetched."""
    fetched = 0
    pages: dict[str, str | None] = {}
    for it in items:
        row = db.one("SELECT checked_at FROM fact_checks WHERE fact_id = ?", (it.id,))
        if http is None or (row and now - (parse_iso(row["checked_at"]) or now) < RECHECK):
            continue
        url = str(it.source_url)
        if url not in pages:
            try:
                pages[url] = http.get(url).text
                fetched += 1
            except FetchError as e:
                log.info("starter pack: can't fetch %s (%s)", url, e.kind)
                pages[url] = None
        text = pages[url]
        status = (
            "unchecked"
            if text is None
            else ("evidence_present" if evidence_present(it.evidence, text) else "page_changed")
        )
        db.execute(
            "INSERT OR REPLACE INTO fact_checks (fact_id, source_url, checked_at, status) VALUES (?,?,?,?)",
            (it.id, url, iso(now), status),
        )
    return fetched


def with_status(db: Database, items: list[StarterItem]) -> list[StarterItem]:
    out = []
    for it in items:
        row = db.one("SELECT checked_at, status FROM fact_checks WHERE fact_id = ?", (it.id,))
        if row:
            it = it.model_copy(update={"check_status": row["status"], "last_checked": parse_iso(row["checked_at"])})
        out.append(it)
    return out
