from __future__ import annotations

from urllib.parse import urlsplit

from sro.domain.shared.hosts import domain_matches

__all__ = ["belongs_to", "domain_matches"]


def belongs_to(cookie: dict[str, object], url: str) -> bool:
    return domain_matches(urlsplit(url).hostname or "", str(cookie.get("domain", "")))
