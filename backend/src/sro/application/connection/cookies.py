"""Whether a stored cookie belongs to the host we are about to send it to.

Both places that asked this asked it as ``host.endswith(domain)``, with a bare
substring test as a second chance. ``"evil-wms.acme.com".endswith("wms.acme.com")``
is true, and so is ``"wms.acme.com" in "wms.acme.com.attacker.test"`` -- so a
lookalike host was read as carrying the customer's session, and could be handed
one. Browsers have never matched this way: a cookie for ``acme.com`` goes to
``acme.com`` and to its subdomains, and to nothing that merely ends with it.
"""

from __future__ import annotations

from urllib.parse import urlsplit


def domain_matches(host: str, cookie_domain: str) -> bool:
    """RFC 6265 domain-match: the host itself, or a subdomain of it."""
    host, domain = host.lower().rstrip("."), cookie_domain.lower().lstrip(".").rstrip(".")
    if not host or not domain:
        return False
    return host == domain or host.endswith(f".{domain}")


def belongs_to(cookie: dict[str, object], url: str) -> bool:
    """Whether ``cookie`` would be sent to ``url``, by domain alone."""
    return domain_matches(urlsplit(url).hostname or "", str(cookie.get("domain", "")))
