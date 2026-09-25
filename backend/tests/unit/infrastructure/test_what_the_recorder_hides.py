"""What the page-side recorder drops before it leaves the browser.

Both directions matter and they pull against each other. A password typed into
a customer's system must never reach the evidence plane. Everything else must,
because the evidence plane is the only account of what the operator did -- and
an address search box that came back as «secret» took the searched-for value
out of the demonstration, out of the description a model wrote from it, and out
of the parameters the skill could have offered.
"""

from __future__ import annotations

import json
import re

import pytest

from sro.infrastructure.steel.capture import _recorder_script


def _words(text: str) -> list[str]:
    """The same split the recorder does, so this tests the rule rather than JS."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return [word.lower() for word in re.split(r"[^A-Za-z]+", spaced) if word]


def _secret_words() -> set[str]:
    """Read out of the script as it is actually injected, list and all: the JS
    used to carry its own copy of these words, and the copies drifted."""
    source = _recorder_script()
    start = source.index("SECRET_WORDS = new Set(")
    listing = source[source.index("[", start) : source.index("]", start) + 1]
    return set(json.loads(listing))


def _hidden(name: str) -> bool:
    words = _words(name)
    secrets = _secret_words()
    return any(word in secrets for word in words) or "".join(words) in secrets


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
