"""Which sites an observed browser records, and which it never does.

A browser has every site in it. The policy is what stands between "watch the
warehouse system this tenant agreed to" and "watch a person's day", and the two
failure modes are not symmetric: a system missed from the list is a task nobody
gets offered, and a page recorded that nobody meant to record is somebody's day
in an evidence plane that keeps things for thirty days.

The default list is the identity providers and nothing else. Webmail was in it
and was taken out deliberately: the work that starts in a mailbox -- a mail
arrives, somebody reads it, and what it says decides what they do in the WMS --
is a workflow this product exists to learn, and a default that hides half of it
teaches half a task. The asymmetry did not go away; it is paid for somewhere
other than a guessed list of hosts. Capture is off until a tenant agrees to it,
nothing is recorded in a tab nobody pressed Watch on, and a tenant who wants
mailboxes out says so in one call. What these tests hold is that the short list
did not quietly cost any of that.
"""

from __future__ import annotations

import pytest

from sro.domain.observation.policy import DEFAULT_EXCLUSIONS, ObservationPolicy

WMS = "https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG"

WAS_EXCLUDED_BY_DEFAULT = (
    "https://mail.google.com/mail/u/0/#inbox",
    "https://outlook.office.com/mail/",
    "https://outlook.office365.com/mail/inbox",
    "https://outlook.cloud.microsoft/mail/",
    "https://outlook.live.com/mail/0/",
    "https://mail.yahoo.com/d/folders/1",
)
"""The six webmail hosts the default list used to carry."""


def _on() -> ObservationPolicy:
    return ObservationPolicy().enabled()


def test_nothing_is_observed_until_somebody_says_so() -> None:
    """The absent policy is the refusing one: a deployment that has not had the
    conversation records nothing at all."""
    assert ObservationPolicy().allows(WMS) is False


@pytest.mark.parametrize("mailbox", WAS_EXCLUDED_BY_DEFAULT)
def test_a_mailbox_is_observable_by_default_and_recorded_by_default_nowhere(
    mailbox: str,
) -> None:
    """Both halves, per host, because either half alone is a wrong story.

    All six went out together, so the harm the first assertion prevents is a
    half-removed list -- Gmail learnable and the Microsoft 365 mailbox silently
    not, which is the shape that teaches half a task and looks like it worked.

    The second is the one that stops "observable by default" being read as "we
    record everybody's mail". `allows` is not the whole gate: it says the policy
    does not forbid the host. Recording still needs the tenant's
    `capture_enabled` and somebody pressing Watch on that tab, and with the
    first of those absent the answer is no for a mailbox exactly as it is for
    the WMS.
    """
    assert _on().allows(mailbox) is True
    assert ObservationPolicy().allows(mailbox) is False


def test_the_default_list_is_sign_in_pages_and_nothing_else() -> None:
    """What "deliberately short" means, held as a number rather than as prose.

    A list that grows by one guessed host at a time is how the webmail default
    arrived in the first place. Anything a customer needs kept out is theirs to
    name; this is only the pages where somebody types a password.
    """
    assert DEFAULT_EXCLUSIONS == (
        "accounts.google.com",
        "login.microsoftonline.com",
        "b2clogin.com",
    )


def test_excluding_the_sign_in_page_says_nothing_about_the_mailbox_behind_it() -> None:
    """The identity provider is not a proxy for the mail it signs you into.

    `login.microsoftonline.com` is in the list and matching is host-or-subdomain,
    so it covers the page where somebody types a password and nothing beyond it.
    This used to be described as a hole. It is now the documented meaning of
    pressing Watch on a mailbox, and the harm this prevents is somebody reading
    the identity entries as an answer to "is mail recorded?" -- they are not,
    and the answer is `excluding(...)`.
    """
    policy = _on().excluding(("login.microsoftonline.com",))

    assert policy.allows("https://login.microsoftonline.com/common/oauth2") is False
    assert policy.allows("https://outlook.office.com/mail/") is True, (
        "the sign-in host was never what kept the mailbox out"
    )


def test_a_subdomain_of_an_excluded_host_is_excluded_too() -> None:
    """Why one entry can cover hosts nobody enumerated.

    Azure AD B2C serves every customer from `<tenant>.b2clogin.com`, so the bare
    domain is the only form of that entry which is not a list of tenant names
    this file would have to keep up with. A host-only test would exclude
    `b2clogin.com` itself, which nobody ever visits, and admit every sign-in
    page actually served.
    """
    assert _on().allows("https://blueyonderalphaus.b2clogin.com/oauth2/v2.0") is False
    assert _on().allows("https://contoso.b2clogin.com/oauth2/v2.0/authorize") is False


def test_a_host_that_merely_ends_with_an_excluded_one_is_not() -> None:
    """RFC 6265 matching, not a suffix test.

    `"notaccounts.google.com".endswith("accounts.google.com")` is true, so a
    suffix test would hand any lookalike registration the exclusion -- and, read
    the other way, would let somebody park a name that quietly stops a real
    system being observed. Demonstrated on hosts the default list actually
    carries, so that shortening the list cannot make this pass vacuously.
    """
    assert _on().allows("https://notaccounts.google.com/") is True
    assert _on().allows("https://notb2clogin.com/") is True


def test_the_system_the_tenant_agreed_to_is_still_observed() -> None:
    assert _on().allows(WMS) is True


def test_a_tenant_that_wants_no_mailboxes_observed_says_so_once() -> None:
    """The whole remedy, and it is one call.

    The default moved; the mechanism did not. A tenant who does not want mail in
    the evidence plane names the hosts, gets the old behaviour back for
    themselves alone, and keeps the system they did agree to. Without this test
    the change reads as a decision taken away from them.
    """
    policy = _on().excluding(
        (
            "mail.google.com",
            "outlook.office.com",
            "outlook.office365.com",
            "outlook.cloud.microsoft",
            "outlook.live.com",
            "mail.yahoo.com",
        )
    )

    for mailbox in WAS_EXCLUDED_BY_DEFAULT:
        assert policy.allows(mailbox) is False
    assert policy.allows(WMS) is True


def test_naming_the_systems_refuses_everything_else() -> None:
    """The shape that survives a mail client this file has never heard of: an
    allow-list refuses by default, so the next unforeseen site is out rather
    than in."""
    policy = _on().only(("bf56-kms-wms-web-np2.jdadelivers.com",))

    assert policy.allows(WMS) is True
    assert policy.allows("https://mail.zoho.com/zm/") is False
    assert policy.allows("https://webmail.acme.example/") is False
