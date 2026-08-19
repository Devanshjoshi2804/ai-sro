"""What the vision rung is allowed to send, and what it must refuse.

Both rules are load-bearing in opposite directions. Sending a screen with a
password on it is the failure this exists to prevent; refusing every screen that
merely says "Shipping" is the failure that makes the rung useless, and it is the
one that actually happened -- "pin" is a substring of "shipping", so a warehouse
portal was withheld from the model for showing its own menu.
"""

from __future__ import annotations

import pytest

from sro.application.execution.egress import EgressRefused, prepare
from sro.application.ports.vision import Screen


def _screen(digest: str) -> Screen:
    return Screen(
        image=b"\x89PNG", mime_type="image/png", width=800, height=600, text_digest=digest
    )


@pytest.mark.parametrize(
    "digest",
    ["Inbound Shipping Outbound Picking", "Mapping: 100,200", "Pinned columns", "Spinner"],
)
def test_a_warehouse_word_that_contains_a_secret_word_is_not_a_secret(digest: str) -> None:
    assert prepare(_screen(digest), enabled=True).screen.text_digest == digest


@pytest.mark.parametrize(
    "digest",
    ["Password: 400,300", "Enter your PIN", "passwordField: 10,10", "One-time OTP", "mfa code"],
)
def test_a_screen_entering_a_credential_is_never_sent(digest: str) -> None:
    with pytest.raises(EgressRefused, match="credential field"):
        prepare(_screen(digest), enabled=True)


def test_nothing_is_sent_when_egress_is_switched_off() -> None:
    with pytest.raises(EgressRefused, match="switched off"):
        prepare(_screen("anything at all"), enabled=False)


def test_the_words_that_blind_the_rung_are_words_something_calls_a_credential() -> None:
    """This list refuses a whole screen, so it is deliberately narrower than the
    shared one -- "ssn" printed somewhere on a warehouse page is not reason to
    stop looking at it. Narrower, not different: two lists that could disagree
    are how "passcode" came to be in one and not the other.
    """
    from sro.application.execution.egress import _SECRET_ON_SCREEN
    from sro.domain.recording.sensitivity import SECRET_TOKENS

    assert set(_SECRET_ON_SCREEN) <= SECRET_TOKENS
