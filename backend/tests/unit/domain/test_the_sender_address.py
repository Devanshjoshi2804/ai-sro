"""The sender check compares the one real mailbox of the From header, never an
address that merely appears in it (a display name is the sender's own words)."""

import pytest

from sro.domain.execution.mail_job import sender_address


@pytest.mark.parametrize(
    ("header", "real"),
    [
        ("tanisha@example.com", "tanisha@example.com"),
        ("Tanisha <TANISHA@Example.com>", "tanisha@example.com"),
        ('"bob@corp.com" <attacker@evil.com>', "attacker@evil.com"),
        ("bob@corp.com <attacker@evil.com>", ""),
        ("a@x.com, b@y.com", ""),
        ("a@b@x.com", ""),
        ('"a@b"@x.com', ""),
        ('"x y"@example.com', ""),
        ("a b@example.com", ""),
        ("tanisha@example.com\r\nBcc: x@y.com", ""),
        ("tanisha@exam\N{CYRILLIC SMALL LETTER A}ple.com", ""),
        ("t\N{CYRILLIC SMALL LETTER A}nisha@example.com", ""),
        ("<tanisha@example.com", ""),
        ("", ""),
    ],
)
def test_only_the_one_real_mailbox_counts(header: str, real: str) -> None:
    assert sender_address(header) == real
