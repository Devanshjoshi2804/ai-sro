"""Which sites an observed browser records, and which it never does.

A browser has every site in it. The policy is what stands between "watch the
warehouse system this tenant agreed to" and "watch a person's day", and the two
failure modes are not symmetric: a system missed from the list is a task nobody
gets offered, and a mailbox left in it is correspondence in an evidence plane
that keeps things for thirty days.
"""

from __future__ import annotations

import pytest

from sro.domain.observation.policy import ObservationPolicy

WMS = "https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG"


def _on() -> ObservationPolicy:
    return ObservationPolicy().enabled()


def test_nothing_is_observed_until_somebody_says_so() -> None:
    """The absent policy is the refusing one: a deployment that has not had the
    conversation records nothing at all."""
    assert ObservationPolicy().allows(WMS) is False


@pytest.mark.parametrize(
    "mailbox",
    [
        "https://mail.google.com/mail/u/0/#inbox",
        "https://outlook.office.com/mail/",
        "https://outlook.office365.com/mail/inbox",
        "https://outlook.cloud.microsoft/mail/",
        "https://outlook.live.com/mail/0/",
        "https://mail.yahoo.com/d/folders/1",
    ],
)
def test_a_mailbox_is_never_observed_by_default(mailbox: str) -> None:
    """Corporate mail most of all. The consumer hosts were excluded and the
    Microsoft 365 ones were not, which is exactly the wrong way round: one is
    somebody's holiday photos, the other is the company's correspondence.
    """
    assert _on().allows(mailbox) is False


def test_the_sign_in_page_being_excluded_never_protected_the_mailbox() -> None:
    """Why the gap existed at all. `login.microsoftonline.com` is in the list
    and matching is host-or-subdomain, so it covered the page where somebody
    types a password and nothing behind it."""
    policy = _on().excluding(("login.microsoftonline.com",))

    assert policy.allows("https://login.microsoftonline.com/common/oauth2") is False
    assert policy.allows("https://outlook.office.com/mail/") is True, (
        "this is the hole the default list now closes"
    )


def test_a_subdomain_of_an_excluded_host_is_excluded_too() -> None:
    assert _on().allows("https://eu.outlook.office.com/mail/") is False


def test_a_host_that_merely_ends_with_an_excluded_one_is_not() -> None:
    """RFC 6265 matching, not a suffix test: `notoutlook.office.com` is a
    different registrable name and an exclusion that swallowed it would be an
    exclusion nobody can reason about."""
    assert _on().allows("https://notmail.google.com.example.test/") is True


def test_the_system_the_tenant_agreed_to_is_still_observed() -> None:
    assert _on().allows(WMS) is True


def test_naming_the_systems_refuses_everything_else() -> None:
    """The shape that survives a mail client this file has never heard of: an
    allow-list refuses by default, so the next unforeseen site is out rather
    than in."""
    policy = _on().only(("bf56-kms-wms-web-np2.jdadelivers.com",))

    assert policy.allows(WMS) is True
    assert policy.allows("https://mail.zoho.com/zm/") is False
    assert policy.allows("https://webmail.acme.example/") is False
