"""Host matching. One rule, because three copies of it disagreed once."""

from __future__ import annotations


def domain_matches(host: str, domain: str) -> bool:
    """RFC 6265 domain-match: the host itself, or a subdomain of it.

    A suffix test is not this. ``"evil-wms.acme.com".endswith("wms.acme.com")``
    is true, and that is how a lookalike host reaches a cookie -- or, here, past
    an exclusion.
    """
    host, domain = host.lower().rstrip("."), domain.lower().lstrip(".").rstrip(".")
    if not host or not domain:
        return False
    return host == domain or host.endswith(f".{domain}")
