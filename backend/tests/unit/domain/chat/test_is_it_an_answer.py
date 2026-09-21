"""What is obviously a value, and what is worth a reading.

The cheap tier. Its job is not to decide -- it is to decide what needs no
deciding, so a code typed into a panel never waits on a model and a sentence
never gets taken for a code.
"""

from __future__ import annotations

from sro.domain.chat.asking import Pending
from sro.domain.chat.is_it_an_answer import plainly_a_value, said_as_the_value


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


def test_a_value_the_person_named_themselves_needs_nobody_to_read_it() -> None:
    """The way out of the loop. The reading is told to refuse when it is
    unsure -- right as a default, and it leaves somebody who typed a real
    value with no move except typing it again and being refused again."""
    asking = _asking(missing=("Address",))

    assert said_as_the_value(asking, "Address: testing for new purpose") == (
        "testing for new purpose"
    )
    assert said_as_the_value(asking, "address = SRO Depot One") == "SRO Depot One"


def test_only_the_field_standing_in_front_of_them() -> None:
    """`url: http://…` typed under a question about Address is not a value
    named for Address, and taking it would be the substring matching this
    whole module exists to have replaced."""
    asking = _asking(missing=("Address",))

    assert said_as_the_value(asking, "url: http://wms/clients") is None
    assert said_as_the_value(asking, "Name: SROCL01") is None


def test_a_name_is_the_same_name_however_the_form_spells_it() -> None:
    """The name the job declares is not always the name on the screen in front
    of them: `customertype-longDescription` is asked for as it is declared."""
    asking = _asking(missing=("long_description",))

    assert said_as_the_value(asking, "Long Description: north dock") == "north dock"


def test_naming_the_field_and_saying_nothing_after_it_is_not_a_value() -> None:
    assert said_as_the_value(_asking(missing=("Address",)), "Address:") is None


def test_a_sentence_that_names_no_field_is_read_the_ordinary_way() -> None:
    assert said_as_the_value(_asking(missing=("Address",)), "has reply arrived") is None


def test_a_box_roomy_enough_for_prose_takes_prose() -> None:
    """The whole of this module exists because `HAS REPLY ARRIVED` went into a
    FOUR-character box. A two-thousand-character description is not that box.

    Measured on the deployment 2026-09-20: asked what `Customer Type
    Description` should be, the operator typed `my sro is best` twice and was
    refused twice -- the model calling it "a casual comment or test remark".
    It was the description. Asking a reading to judge somebody's prose is
    asking it a question it cannot answer.
    """
    asking = _asking(missing=("Description",), limits={"Description": 2000})

    assert plainly_a_value(asking, "my sro is best") is True
    assert plainly_a_value(asking, "leaning new SRO type 01, for the north dock") is True


def test_a_question_is_still_a_question_however_roomy_the_box() -> None:
    """The one part of the sentence rule a prose field keeps. A comma and a
    colon are ordinary inside a description; a question mark is the clearest
    signal a person ever gives that they are asking rather than answering."""
    asking = _asking(missing=("Description",), limits={"Description": 2000})

    assert plainly_a_value(asking, "has the reply arrived?") is False
    # And the punctuation prose does carry is not held against it.
    assert plainly_a_value(asking, "north dock, second aisle: overflow only") is True


def test_prose_too_long_for_its_own_box_is_not_obviously_a_value() -> None:
    asking = _asking(missing=("Description",), limits={"Description": 200})

    assert plainly_a_value(asking, "x" * 201) is False


def test_a_short_box_keeps_every_bit_of_the_old_rule() -> None:
    """The four-character box, unchanged. `K_PROSE` is a rule about roomy
    fields and must not have loosened the one this was written for."""
    asking = _asking(limits={"Customer Type": 4})

    assert plainly_a_value(asking, "has reply arrived") is False
    assert plainly_a_value(asking, "GU9") is True
