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


def test_a_host_only_cookie_goes_to_its_own_host_and_nowhere_else() -> None:
    parent = {"name": "sid", "value": "P", "domain": "by.example", "path": "/"}

    assert belongs_to(parent, "https://by.example/")
    assert not belongs_to(parent, "https://wms.by.example/")


def test_a_secure_cookie_never_goes_over_plain_http() -> None:
    secure = {"name": "sid", "value": "S", "domain": "wms.by.example", "secure": True}

    assert belongs_to(secure, "https://wms.by.example/app")
    assert not belongs_to(secure, "http://wms.by.example/app")


def test_a_cookie_goes_only_under_its_path() -> None:
    admin = {"name": "a", "value": "A", "domain": "wms.by.example", "path": "/admin"}

    assert belongs_to(admin, "https://wms.by.example/admin")
    assert belongs_to(admin, "https://wms.by.example/admin/users")
    assert not belongs_to(admin, "https://wms.by.example/")
    assert not belongs_to(admin, "https://wms.by.example/administrator")
    assert belongs_to({**admin, "path": "/"}, "https://wms.by.example")


def test_a_url_without_a_scheme_carries_no_cookie() -> None:
    session = {"name": "sid", "value": "1", "domain": "wms.by.example"}

    assert not belongs_to(session, "wms.by.example")
