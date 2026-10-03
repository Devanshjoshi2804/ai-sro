"""What the page-side recorder drops before it leaves the browser.

Both directions matter and they pull against each other. A password typed into
a customer's system must never reach the evidence plane. Everything else must,
because the evidence plane is the only account of what the operator did -- and
an address search box that came back as «secret» took the searched-for value
out of the demonstration, out of the description a model wrote from it, and out
of the parameters the skill could have offered.
"""

from __future__ import annotations

import pytest

from sro.domain.recording.sensitivity import is_secret_field
from sro.infrastructure.steel.capture import _recorder_script


def _hidden(name: str) -> bool:
    """The one rule, from sensitivity.py -- the recorder's copy is generated from it."""
    return is_secret_field(name)


@pytest.mark.parametrize(
    "field",
    [
        "wmAddress-1423-inputEl",
        "Supplier* What is the supplier number?",
        "shippingNotes",
        "passenger_count",
        "pincode",
        "description",
        "clientId",
    ],
)
def test_ordinary_business_fields_are_kept(field: str) -> None:
    assert not _hidden(field), f"{field} is not a credential"


@pytest.mark.parametrize(
    "field",
    ["j_password", "userPassword", "api_key", "Enter your PIN", "otp", "refreshToken"],
)
def test_a_credential_never_leaves_the_page(field: str) -> None:
    assert _hidden(field)


def test_the_page_s_own_declaration_is_still_believed() -> None:
    """`type=password` and the autocomplete tokens are decisions the site made,
    not guesses about a name, and they stay authoritative."""
    source = _recorder_script()
    assert '"password"' in source and "one-time-code" in source


@pytest.mark.parametrize(
    "field",
    ["Verification Code", "One-time code", "Passcode", "verificationCode", "otp"],
)
def test_a_code_that_lives_for_a_minute_is_still_a_credential(field: str) -> None:
    """None of the three lists had these. A WMS that mails a six-digit code
    called it a "Verification Code", so the recorder kept it verbatim and
    induction went on to offer it as a parameter to store, display and replay.
    """
    assert _hidden(field)


@pytest.mark.parametrize(
    "field",
    ["Login code", "Enter your login code", "enter verification code", "one time code", "pwd"],
)
def test_a_phrase_that_names_a_short_lived_credential_is_hidden(field: str) -> None:
    assert _hidden(field)


@pytest.mark.parametrize(
    "field",
    ["Customer type code", "Postal code", "Code", "Zip code", "Dock door code", "Status code"],
)
def test_a_job_field_that_ends_in_code_stays_capturable(field: str) -> None:
    """Bare `code` is a warehouse word (138 field names end in it): only the
    named credential phrases hide, never the word on its own."""
    assert not _hidden(field)
