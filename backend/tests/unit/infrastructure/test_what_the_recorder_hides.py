"""What the page-side recorder drops before it leaves the browser.

Both directions matter and they pull against each other. A password typed into
a customer's system must never reach the evidence plane. Everything else must,
because the evidence plane is the only account of what the operator did -- and
an address search box that came back as «secret» took the searched-for value
out of the demonstration, out of the description a model wrote from it, and out
of the parameters the skill could have offered.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_RECORDER = Path(__file__).resolve().parents[3] / "src/sro/infrastructure/steel/recorder.js"


def _words(text: str) -> list[str]:
    """The same split the recorder does, so this tests the rule rather than JS."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return [word.lower() for word in re.split(r"[^A-Za-z]+", spaced) if word]


def _secret_words() -> set[str]:
    source = _RECORDER.read_text()
    start = source.index("SECRET_WORDS = new Set([")
    return set(re.findall(r"'([a-z]+)'", source[start : source.index("]);", start)]))


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
    source = _RECORDER.read_text()
    assert "'password'" in source and "one-time-code" in source
