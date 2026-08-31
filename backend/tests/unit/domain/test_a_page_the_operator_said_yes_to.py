"""The exclusion list is a default, and a default is something a person may
decide otherwise about for one page of their own.

Webmail is excluded for everyone, deliberately: continuous capture of somebody's
mailbox is what needs a DPIA and what employee consent cannot make lawful. The
cost of that is that a task involving the operator's mail could never be
demonstrated at all -- press teach in a mailbox and the recording came back
empty.

A grant is the other act. One host, chosen by the person whose browser it is,
for the tab in front of them, visible in the panel while it lasts, gone when
they close the tab. What these tests hold is the difference between the two,
because a grant that quietly became the first is the exclusion list undone.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sro.domain.observation.grant import LONGEST, HostGrant
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.plan import UiPlan
from sro.domain.skill.skill import SkillStep
from sro.domain.skill.template import Template
from sro.domain.skill.track_record import why_not_autonomous
from tests import factories as f

AT = datetime(2026, 8, 30, 9, 0, tzinfo=UTC)
MAIL = "https://mail.google.com/mail/u/0"
WMS = "https://wms.acme.test/waves"

WATCHED = ObservationPolicy().enabled().excluding(("mail.google.com",))


def _grant(host: str, *, at: datetime = AT, lasting: timedelta = timedelta(hours=1)) -> HostGrant:
    return HostGrant(host=host, granted_by=f.OPERATOR, granted_at=at, expires_at=at + lasting)


def test_an_excluded_page_is_not_observed_without_one() -> None:
    assert WATCHED.allows(MAIL) is False


def test_the_operator_saying_yes_admits_that_one_host() -> None:
    assert WATCHED.allows(MAIL, frozenset({"mail.google.com"})) is True


def test_a_grant_admits_that_host_and_not_the_domain_under_it() -> None:
    # `hostMatches` is right for a policy pattern an administrator wrote and
    # wrong here: somebody pressed a button while looking at one page, and
    # reading it as a whole domain would admit every host beneath it.
    granted = frozenset({"mail.google.com"})

    assert WATCHED.allows("https://inbox.mail.google.com/x", granted) is False


def test_a_grant_cannot_switch_observation_on() -> None:
    # `capture_enabled` is the tenant agreeing that any of this happens at all.
    # No button in anybody's side panel is allowed to be that agreement.
    off = ObservationPolicy().excluding(("mail.google.com",))

    assert off.allows(MAIL, frozenset({"mail.google.com"})) is False
    assert off.allows(WMS, frozenset({"wms.acme.test"})) is False


def test_a_grant_does_not_widen_an_administrators_list_of_what_may_be_observed() -> None:
    # `exclude_hosts` is a default. `include_hosts` is somebody naming the only
    # hosts that may ever be observed here, which is a decision an operator
    # does not get to overrule from a side panel.
    named = ObservationPolicy().enabled().only(("wms.acme.test",))

    assert named.allows(MAIL, frozenset({"mail.google.com"})) is False
    assert named.allows(WMS) is True


def test_a_grant_that_has_run_out_admits_nothing() -> None:
    device = f.device(grants=(_grant("mail.google.com", lasting=timedelta(hours=1)),))

    assert device.granted_hosts(AT + timedelta(minutes=59)) == frozenset({"mail.google.com"})
    assert device.granted_hosts(AT + timedelta(hours=2)) == frozenset()


def test_a_grant_may_not_outlast_a_browser_that_stopped_without_revoking() -> None:
    with pytest.raises(InvariantViolation, match="at most"):
        _grant("mail.google.com", lasting=LONGEST + timedelta(minutes=1))


def test_granting_the_same_host_twice_keeps_the_later_expiry() -> None:
    # The operator pressing the button again means "keep watching". A device
    # that kept both rows would expire on the older of them.
    device = f.device()
    device.grant("mail.google.com", by=f.OPERATOR, at=AT, until=AT + timedelta(hours=1))
    device.grant(
        "mail.google.com",
        by=f.OPERATOR,
        at=AT + timedelta(minutes=30),
        until=AT + timedelta(hours=6),
    )

    assert len(device.grants) == 1
    assert device.granted_hosts(AT + timedelta(hours=2)) == frozenset({"mail.google.com"})


def test_revoking_gives_the_page_back() -> None:
    device = f.device(grants=(_grant("mail.google.com"),))

    device.revoke("mail.google.com")

    assert device.granted_hosts(AT) == frozenset()


def test_a_grant_is_stored_the_way_a_url_will_be_compared() -> None:
    # `ObservationPolicy.allows` reads a hostname, which is already lowercase.
    # A grant on `Mail.Google.com` would match nothing while looking exactly
    # like it should.
    with pytest.raises(InvariantViolation, match="normalised"):
        _grant("Mail.Google.com")


def test_a_skill_with_a_gesture_step_is_told_it_can_never_run_unattended() -> None:
    """Not "not yet" -- not ever, and the difference is the whole message.

    A step with no call behind it is performed by clicking; `judge` calls any
    run that performs one degraded, and a degraded run resets the streak. The
    count alone would sit at zero forever while reading like a skill that had
    simply not had a good week.
    """
    checked = (Assertion(kind=AssertionKind.HTTP_STATUS, expected=Template("200")),)
    clicking = f.skill_version(
        steps=(
            f.step(index=0, assertions=checked),
            SkillStep(index=1, intent="Press send", ui_plan=UiPlan(action="click", target="Send")),
        ),
    )

    reason = why_not_autonomous(
        clicking.track_record,
        verifiable=clicking.verifiable,
        needs_a_person=clicking.needs_a_person,
    )

    assert reason is not None
    assert "never unattended" in reason
    assert "clicking" in reason


def test_a_skill_that_is_only_calls_is_told_how_far_it_has_got() -> None:
    calls = f.skill_version(
        steps=(
            f.step(
                index=0,
                assertions=(Assertion(kind=AssertionKind.HTTP_STATUS, expected=Template("200")),),
            ),
        )
    )

    reason = why_not_autonomous(
        calls.track_record, verifiable=calls.verifiable, needs_a_person=calls.needs_a_person
    )

    assert reason is not None
    assert "clean runs in a row" in reason
