"""Whether a stored cookie belongs to the host about to receive it.

Both callers asked ``host.endswith(domain)``, with a substring test as a second
chance. Registering ``evil-wms.acme.com`` passes the first; registering
``wms.acme.com.attacker.test`` passes the second. Either one reads as carrying
the customer's session -- and one of the two callers then decides a browser is
signed in to their WMS and drives it.
"""

from __future__ import annotations

import pytest

from sro.application.connection.cookies import belongs_to, domain_matches


@pytest.mark.parametrize(
    ("host", "domain"),
    [
        ("wms.acme.com", "wms.acme.com"),
        ("wms.acme.com", ".acme.com"),
        ("a.b.acme.com", "acme.com"),
        ("WMS.Acme.com", "acme.com"),
    ],
)
def test_the_host_itself_and_its_subdomains_match(host: str, domain: str) -> None:
    assert domain_matches(host, domain)


@pytest.mark.parametrize(
    ("host", "domain"),
    [
        ("evil-wms.acme.com", "wms.acme.com"),
        ("wms.acme.com.attacker.test", "wms.acme.com"),
        ("acme.com", "wms.acme.com"),
        ("acme.com.evil.test", "acme.com"),
        ("", "acme.com"),
        ("acme.com", ""),
    ],
)
def test_a_lookalike_does_not(host: str, domain: str) -> None:
    assert not domain_matches(host, domain)


def test_a_cookie_is_read_against_the_url_it_would_be_sent_to() -> None:
    session = {"name": "JSESSIONID", "value": "1", "domain": ".acme.com"}

    assert belongs_to(session, "https://wms.acme.com/portal")
    assert not belongs_to(session, "https://acme.com.attacker.test/portal")
