"""Host matching. One rule, because three copies of it disagreed once."""

from __future__ import annotations

from urllib.parse import urlparse

# The marker a redaction leaves behind, in place of whatever it removed. Lives
# here, beside `system_of`, rather than in the wire module that first defined
# it: both a body redaction and a URL's origin are things more than one module
# in this codebase reads, and a rule two copies of which had already
# disagreed once is exactly the kind of thing this module exists to hold once.
REDACTED = "«redacted»"


def system_of(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


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
