"""Whether a stored cookie belongs to the host we are about to send it to.

Both places that asked this asked it as ``host.endswith(domain)``, with a bare
substring test as a second chance. ``"evil-wms.acme.com".endswith("wms.acme.com")``
is true, and so is ``"wms.acme.com" in "wms.acme.com.attacker.test"`` -- so a
lookalike host was read as carrying the customer's session, and could be handed
one. Browsers have never matched this way: a cookie for ``acme.com`` goes to
``acme.com`` and to its subdomains, and to nothing that merely ends with it.

The rule itself moved to ``domain/shared/hosts.py`` when observation policy
needed the same one to decide whether a page is excluded from capture.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from sro.domain.shared.hosts import domain_matches

__all__ = ["belongs_to", "domain_matches"]


def belongs_to(cookie: dict[str, object], url: str) -> bool:
    """Whether ``cookie`` would be sent to ``url``, by domain alone."""
    return domain_matches(urlsplit(url).hostname or "", str(cookie.get("domain", "")))
