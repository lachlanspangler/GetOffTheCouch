"""Source-agnostic normalization applied to every adapter record *before* schema validation.

Adapters stay small; tricks that help every source live here:
  * ``_html``: the raw description HTML. Sign-up / ticket / RSVP links are lifted out as offers
    (I-012), because "Sign up here" links vanish when HTML is flattened to text.
  * missing location → "Location: …" / "Where: …" / "Meet at …" lines in the description (I-011)
  * volunteering is free by definition → ``price.is_free`` (derived; labeled in provenance) (I-015)
"""

from __future__ import annotations

import html as htmllib
import re
from typing import Any
from urllib.parse import urlsplit

from gotc.adapters.common import clean_text

_A = re.compile(r"""<a\s[^>]*?href\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>""", re.I | re.S)

# hosts that are, by themselves, a strong signal of a registration/ticket page
REG_HOSTS = {
    "signupgenius.com": "registration",
    "volunteerhub.com": "registration",
    "galaxydigital.com": "registration",
    "givepulse.com": "registration",
    "volunteermatch.org": "registration",
    "jotform.com": "registration",
    "forms.gle": "registration",
    "docs.google.com": "registration",
    "apm.activecommunities.com": "registration",
    "secure.rec1.com": "registration",
    "leagueapps.com": "registration",
    "volosports.com": "registration",
    "runsignup.com": "registration",
    "raceroster.com": "registration",
    "eventbrite.com": "rsvp",
    "eventbrite.co": "rsvp",
    "ticketmaster.com": "primary",
    "axs.com": "primary",
    "etix.com": "primary",
    "dice.fm": "primary",
    "seetickets.us": "primary",
    "tixr.com": "primary",
    "universe.com": "primary",
    "seatgeek.com": "resale",
    "stubhub.com": "resale",
    "vividseats.com": "resale",
}
_TEXT_KIND = [
    (re.compile(r"\b(sign[- ]?up|register|registration|enroll|volunteer (here|now)|apply)\b", re.I), "registration"),
    (re.compile(r"\b(rsvp)\b", re.I), "rsvp"),
    (re.compile(r"\b(tickets?|buy now|purchase)\b", re.I), "primary"),
]
_BARE = re.compile(r"https?://[^\s<>\"']+")
_LOC = re.compile(r"(?im)^\s*(?:location|where|place|venue|meet(?:ing)? (?:at|location|point))\s*[:\-–]\s*(.{3,140})$")


def links_from_html(html: str | None) -> list[tuple[str, str, str]]:
    """Return (kind, url, anchor text) for links that look like registration/ticket/RSVP pages."""
    if not html:
        return []
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for href, inner in _A.findall(html):
        url = htmllib.unescape(href).strip()
        if not url.startswith(("http://", "https://")) or url in seen:
            continue
        text = clean_text(inner) or ""
        host = urlsplit(url).netloc.lower().removeprefix("www.")
        kind = next((k for h, k in REG_HOSTS.items() if host == h or host.endswith("." + h)), None)
        if kind is None:
            kind = next((k for pat, k in _TEXT_KIND if pat.search(text)), None)
        if kind:
            seen.add(url)
            out.append((kind, url, text[:80]))
    for url in _BARE.findall(_A.sub(" ", html)):  # bare URLs in plain text: trust the host only
        url = htmllib.unescape(url).rstrip(".,);]")
        host = urlsplit(url).netloc.lower().removeprefix("www.")
        kind = next((k for h, k in REG_HOSTS.items() if host == h or host.endswith("." + h)), None)
        if kind and url not in seen:
            seen.add(url)
            out.append((kind, url, ""))
    return out


def location_from_text(text: str | None) -> str | None:
    if not text:
        return None
    m = _LOC.search(text)
    if not m:
        return None
    loc = m.group(1).strip(" .")
    loc = re.split(r"\s{2,}|\.\s|(?i:\bsupplies\b|\bhost\b|\bdates?\b)\s*:", loc)[0].strip(" .,")
    return loc or None


_CANCELLED = re.compile(r"^\s*\[?\(?(cancel+ed|postponed)\b[\]):\s-]*", re.I)
# University/institution feeds mix public events with internal ones. Only applied to sources that opt in
# (params.audience_filter: institution). Matches are *skipped* (counted), not rejected — they're valid, just not for us.
_INTERNAL = re.compile(
    r"\b(faculty|staff|employees?|students?|alumni|members|residents?) only\b"
    r"|\bfor (current |enrolled |admitted )?(\w+ )?(students|faculty|staff|employees)\b"
    r"|\b(dissertation|thesis|prospectus|qualifying exam|defen[cs]e of)\b"
    r"|\b(office hours|colloquium|faculty meeting|staff meeting|board meeting|e-board|department meeting|lab meeting)\b"
    r"|\b(orientation for|advising|registrar|commencement rehearsal|info session for (graduate|undergraduate))\b"
    r"|\b(faculty|staff) (housing|appreciation|development|senate|council)\b"
    r"|\bnot open to the public\b|\bby invitation only\b|\binvite only\b|\bclosed to the public\b"
    r"|\b(TA|RA) - |\bfixed pros\b",
    re.I,
)


def audience_skip(rec: dict[str, Any], mode: str | None) -> str | None:
    if mode != "institution":
        return None
    text = f"{rec.get('title') or ''} \n {(rec.get('description') or '')[:600]}"
    m = _INTERNAL.search(text)
    return f"not public: {m.group(0)!r}" if m else None


def normalize_record(rec: dict[str, Any], source_name: str) -> dict[str, Any]:
    raw_html = rec.pop("_html", None)
    title = str(rec.get("title") or "")
    if m := _CANCELLED.match(title):
        rec["availability"] = "postponed" if m.group(1).lower().startswith("post") else "cancelled"
    offers = list(rec.get("offers") or [])
    have = {str(o.get("url")) for o in offers}
    for kind, url, _text in links_from_html(raw_html):
        if url in have or len(offers) >= 4:
            continue
        host = urlsplit(url).netloc.removeprefix("www.")
        offers.append(
            {
                "seller": _seller_name(host, source_name),
                "kind": "resale" if kind == "resale" else kind,
                "url": url,
                "source_id": rec["source_id"],
                "fetched_at": rec["fetched_at"],
                "availability": "registration_open" if kind == "registration" else "unknown",
            }
        )
        have.add(url)
    if offers:
        rec["offers"] = offers

    loc = dict(rec.get("location") or {})
    if not loc.get("venue_name") and not loc.get("address") and loc.get("lat") is None:
        found = location_from_text(rec.get("description"))
        if found:
            loc.update({"venue_name": found.split(",")[0][:120], "address": found})
            rec["location"] = loc
            extras = dict(rec.get("extras") or {})
            extras["location_from"] = "description"
            rec["extras"] = extras

    price = dict(rec.get("price") or {})
    if str(rec.get("category", "")).startswith("volunteer.") and not price.get("min") and not price.get("max"):
        price["is_free"] = True
        price.setdefault("note", "volunteering (free)")
        rec["price"] = price
        if rec.get("availability") in (None, "unknown"):
            rec["availability"] = "registration_open" if offers else "free_no_ticket"
    return rec


_SELLERS = {
    "signupgenius.com": "SignUpGenius",
    "eventbrite.com": "Eventbrite",
    "volunteerhub.com": "VolunteerHub",
    "givepulse.com": "GivePulse",
    "volunteermatch.org": "VolunteerMatch",
    "ticketmaster.com": "Ticketmaster",
    "axs.com": "AXS",
    "etix.com": "Etix",
    "dice.fm": "DICE",
    "seatgeek.com": "SeatGeek",
    "stubhub.com": "StubHub",
    "vividseats.com": "Vivid Seats",
    "runsignup.com": "RunSignup",
    "leagueapps.com": "LeagueApps",
    "volosports.com": "Volo",
    "forms.gle": "Google Forms",
    "docs.google.com": "Google Forms",
}


def _seller_name(host: str, fallback: str) -> str:
    for h, name in _SELLERS.items():
        if host == h or host.endswith("." + h):
            return name
    return fallback
