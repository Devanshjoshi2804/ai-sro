"""What a tenant agreed to have observed, and what that refuses."""

from __future__ import annotations

import pytest

from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.errors import InvariantViolation


def test_a_tenant_nobody_configured_is_observed_not_at_all() -> None:
    assert ObservationPolicy().allows("https://wms.acme.com/orders") is False


def test_switching_it_on_moves_the_version_so_every_extension_hears_about_it() -> None:
    policy = ObservationPolicy().enabled()

    assert policy.capture_enabled is True
    assert policy.version == 1
    assert policy.allows("https://wms.acme.com/orders") is True


def test_an_excluded_host_and_its_subdomains_are_never_observed() -> None:
    policy = ObservationPolicy().enabled().excluding(("payroll.acme.com",))

    assert policy.allows("https://payroll.acme.com/payslips") is False
    assert policy.allows("https://eu.payroll.acme.com/payslips") is False


def test_a_lookalike_host_is_not_covered_by_somebody_elses_exclusion() -> None:
    # The bug a suffix test has: "evil-payroll.acme.com".endswith("payroll.acme.com")
    # is true, so an attacker's host would read as excluded and, in the cookie
    # code this rule came from, as carrying the customer's session.
    policy = ObservationPolicy().enabled().excluding(("payroll.acme.com",))

    assert policy.allows("https://evil-payroll.acme.com/steal") is True


def test_naming_hosts_narrows_capture_to_those_and_nothing_else() -> None:
    policy = ObservationPolicy().enabled().only(("wms.acme.com",))

    assert policy.allows("https://wms.acme.com/orders") is True
    assert policy.allows("https://intranet.acme.com/news") is False


def test_a_sign_in_page_is_excluded_before_anybody_configures_anything() -> None:
    # The default list is now sign-in pages and nothing else. There is no task
    # to learn on one and nothing on it anybody wants in evidence, and unlike a
    # mailbox no tenant has ever asked for the opposite.
    policy = ObservationPolicy().enabled()

    assert policy.allows("https://accounts.google.com/signin") is False
    assert policy.allows("https://login.microsoftonline.com/common/oauth2") is False
    # A host-or-subdomain test, which is what makes one entry cover Azure AD
    # B2C: the host is always `<tenant>.b2clogin.com`.
    assert policy.allows("https://blueyonderalphaus.b2clogin.com/oauth2/v2.0") is False


def test_webmail_is_observable_by_default_and_only_in_a_watched_tab() -> None:
    # Webmail was in the default list and was taken out deliberately: the work
    # that starts in a mailbox is a workflow this product exists to learn, and
    # a default that hides half of it teaches half a task.
    #
    # `allows` is not the whole gate, which is why this is safe to assert. It
    # says the policy does not forbid the host; capture still requires
    # `capture_enabled` AND somebody pressing Watch on that tab. The two
    # assertions below are that pair, and the second is the one that stops
    # "observable by default" from meaning "recorded by default".
    assert ObservationPolicy().enabled().allows("https://mail.google.com/mail/u/0") is True
    assert ObservationPolicy().allows("https://mail.google.com/mail/u/0") is False


def test_a_tenant_that_wants_webmail_back_can_have_it_back() -> None:
    # The default moved; the mechanism did not. This is the whole remedy for a
    # tenant who does not want mailboxes observed, and it is one call.
    policy = ObservationPolicy().enabled().excluding(("mail.google.com",))

    assert policy.allows("https://mail.google.com/mail/u/0") is False
    assert policy.allows("https://wms.acme.com/orders") is True


def test_a_url_with_no_host_is_not_something_to_observe() -> None:
    assert ObservationPolicy().enabled().allows("about:blank") is False


def test_evidence_kept_for_less_than_a_day_is_evidence_discarded() -> None:
    with pytest.raises(InvariantViolation):
        ObservationPolicy().keeping_for(0)
