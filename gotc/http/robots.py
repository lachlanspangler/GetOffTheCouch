"""robots.txt rules with RFC 9309 semantics (the stdlib ``urllib.robotparser`` gets two things wrong for us).

1. **Wildcards.** ``*`` (any run of characters) and a trailing ``$`` (end of URL) are part of RFC 9309 and are
   used by real sites (``Disallow: /*?*``, ``Disallow: /*.pdf$``). The stdlib matches them literally, so it
   *allowed* paths that sites disallow (Downtown Jacksonville's events API, providenceri.gov's query URLs).
2. **Blank lines.** The stdlib ends a group at a blank line, so ``User-agent: *`` / ``Crawl-delay: 5`` /
   *(blank)* / ``Disallow: /wp-json/`` was read as "everything allowed" (clpvd.org, many LibCal hosts). RFC 9309
   groups are delimited only by ``user-agent`` lines; blank lines and comments carry no meaning.

Matching: the group whose user-agent token matches our product token (case-insensitive) wins, else the ``*``
group(s); same-agent groups are merged. Within the group the longest matching path pattern decides and
``allow`` wins a tie. An empty ``Disallow:`` allows everything. Paths are compared with the query string.
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass
class _Group:
    agents: list[str] = field(default_factory=list)
    rules: list[tuple[bool, str]] = field(default_factory=list)  # (allow?, pattern)
    crawl_delay: float | None = None


def _pattern(p: str) -> re.Pattern[str]:
    anchored = p.endswith("$")
    body = re.escape(p[:-1] if anchored else p).replace(r"\*", ".*")
    return re.compile(body + ("$" if anchored else ""))


class RobotsRules:
    def __init__(self, text: str) -> None:
        self.groups: list[_Group] = []
        cur: _Group | None = None
        in_agents = False
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue  # blank lines / comments / junk never end a group (RFC 9309 §2.2)
            key, _, value = line.partition(":")
            key, value = key.strip().lower(), value.strip()
            if key == "user-agent":
                if cur is None or not in_agents:
                    cur = _Group()
                    self.groups.append(cur)
                cur.agents.append(value.lower())
                in_agents = True
                continue
            in_agents = False
            if cur is None:
                continue  # rules before any user-agent line belong to no group
            if key in ("allow", "disallow"):
                cur.rules.append((key == "allow", value))
            elif key == "crawl-delay":
                with contextlib.suppress(ValueError):
                    cur.crawl_delay = float(value)

    @staticmethod
    def _token(user_agent: str) -> str:
        return user_agent.split("/", 1)[0].strip().lower()

    def _groups_for(self, user_agent: str) -> list[_Group]:
        token = self._token(user_agent)
        mine = [g for g in self.groups if any(a != "*" and self._token(a) == token for a in g.agents)]
        return mine or [g for g in self.groups if "*" in g.agents]

    def can_fetch(self, user_agent: str, url: str) -> bool:
        parts = urlsplit(url)
        path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        if path == "/robots.txt":
            return True
        best: tuple[int, bool] | None = None
        for g in self._groups_for(user_agent):
            for allow, pat in g.rules:
                if not pat:
                    continue  # "Disallow:" (empty) = allow all
                if _pattern(pat).match(path):
                    score = len(pat)
                    if best is None or score > best[0] or (score == best[0] and allow):
                        best = (score, allow)
        return True if best is None else best[1]

    def crawl_delay(self, user_agent: str) -> float | None:
        delays = [g.crawl_delay for g in self._groups_for(user_agent) if g.crawl_delay is not None]
        return max(delays) if delays else None
