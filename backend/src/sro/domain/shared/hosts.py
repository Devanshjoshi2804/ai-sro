"""Host matching. One rule, because three copies of it disagreed once."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlparse, urlsplit

# The marker a redaction leaves behind, in place of whatever it removed. Lives
# here, beside `system_of`, rather than in the wire module that first defined
# it: both a body redaction and a URL's origin are things more than one module
# in this codebase reads, and a rule two copies of which had already
# disagreed once is exactly the kind of thing this module exists to hold once.
REDACTED = "«redacted»"


_DEFAULT_PORTS = {"http": "80", "https": "443"}


def origin_of(url: str) -> str:
    """A url as the system it belongs to: host and port, default port dropped.

    `https://wms.acme.com:443` and `https://wms.acme.com` are one system, and
    a rule that cannot say so refuses half the pages on it. Port and not
    hostname alone, because an API on 8000 beside a console on 3000 is the
    ordinary shape of this deployment.

    Here rather than in `skill/checks.py`, where it was written, because the
    evidence plane needs the same idea of what one system is: the rule that
    links two systems by TIME has to agree with the rule that strikes a
    system from a job about whether a port makes two of them.
    """
    parsed = urlsplit(url)
    host = (parsed.hostname or "").rstrip(".")
    if not host:
        return ""
    if ":" in host:
        host = f"[{host}]"
    try:
        port = str(parsed.port) if parsed.port else ""
    except ValueError:
        return ""
    if port and port == _DEFAULT_PORTS.get(parsed.scheme.lower()):
        port = ""
    return f"{host}:{port}" if port else host


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


def headers_without_markers(headers: Mapping[str, str]) -> dict[str, str]:
    """The headers that can still be sent: a value the boundary struck out is
    not a credential the browser can use, it is the marker's own text. Beside
    REDACTED because everything that sends a recorded request needs the same
    rule -- the planner replaying a call, the verifier probing a confirming
    read, the lookup addressing an endpoint -- and a second copy is a second
    thing to forget."""
    return {name: value for name, value in headers.items() if REDACTED not in value}
