"""What a reply says is what the person typed: the mail it quotes is the
system's own earlier words, never an answer."""

from sro.domain.chat.mail_reply import without_the_quote


def test_a_quoted_line_is_not_what_was_typed() -> None:
    assert without_the_quote("use another one\n> Customer Type GT2\n> Description x") == (
        "use another one"
    )


def test_an_inline_answer_under_the_attribution_line_is_kept() -> None:
    body = "On Tue, 29 Sep 2026 at 10:00, AI-SRO <a@x.com> wrote:\n> Which value?\nVets"
    assert without_the_quote(body) == "Vets"


def test_an_attribution_wrapped_over_two_lines_is_dropped() -> None:
    body = (
        "Vets\n\nOn Tue, 29 Sep 2026 at 10:00, Some Person <a@x.com>\nwrote:\n> Customer Type GT2"
    )
    assert without_the_quote(body) == "Vets"


def test_an_original_message_block_and_all_after_it_are_dropped() -> None:
    body = "Vets\n\n-----Original Message-----\nFrom: a@x.com\nCustomer Type GT2"
    assert without_the_quote(body) == "Vets"


def test_an_outlook_header_block_and_all_after_it_are_dropped() -> None:
    body = (
        "Vets\n________________________________\nFrom: A <a@x.com>\nSent: Tuesday\n"
        "To: b@x.com\nSubject: x\n\nCustomer Type GT2"
    )
    assert without_the_quote(body) == "Vets"


def test_a_line_that_only_starts_with_from_is_text() -> None:
    assert without_the_quote("From Monday use Vets\nthanks") == "From Monday use Vets\nthanks"


def test_nothing_quoted_is_unchanged() -> None:
    assert without_the_quote("Description :- Vets") == "Description :- Vets"
