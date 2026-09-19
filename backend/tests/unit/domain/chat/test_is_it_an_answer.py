"""What is obviously a value, and what is worth a reading.

The cheap tier. Its job is not to decide -- it is to decide what needs no
deciding, so a code typed into a panel never waits on a model and a sentence
never gets taken for a code.
"""

from __future__ import annotations

from sro.domain.chat.asking import Pending
from sro.domain.chat.is_it_an_answer import plainly_a_value


def _asking(**over: object) -> Pending:
    fields: dict[str, object] = {
        "workflow_id": "wfl_1",
        "title": "Create a Customer Type",
        "values": {},
        "missing": ("Customer Type",),
    }
    fields.update(over)
    return Pending(**fields)


def test_a_code_is_a_value_and_costs_nothing_to_know_it() -> None:
    assert plainly_a_value(_asking(), "S057") is True
    assert plainly_a_value(_asking(), "  GU9  ") is True


def test_a_sentence_is_not_obviously_a_value() -> None:
    """Not "this is not an answer" -- "this is worth asking about". `the code
    is S057` answers the question and is read; `has reply arrived` does not."""
    assert plainly_a_value(_asking(), "has reply arrived") is False
    assert plainly_a_value(_asking(), "the code is S057") is False


def test_a_question_mark_is_never_obviously_a_value() -> None:
    """The clearest signal a person ever gives that they are asking rather
    than answering, and this system used to throw it away."""
    assert plainly_a_value(_asking(), "ready?") is False


def test_a_word_the_box_will_not_hold_is_not_obvious_either() -> None:
    """It is refused further down whatever this says. But a lone word too long
    for the field is not OBVIOUSLY the value, and obviousness is the whole of
    what this decides -- a reading may well find the code inside it."""
    asking = _asking(limits={"Customer Type": 4})

    assert plainly_a_value(asking, "S057") is True
    assert plainly_a_value(asking, "NEWSROTEST") is False


def test_nothing_typed_is_not_a_value() -> None:
    assert plainly_a_value(_asking(), "   ") is False
