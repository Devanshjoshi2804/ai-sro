"""What a conversation is waiting on, and what an answer does to it."""

from __future__ import annotations

from datetime import UTC, datetime

from sro.domain.chat.asking import (
    NEEDS,
    Pending,
    _step,
    answered,
    let_go,
    pending_job,
    question,
    unusable,
)
from sro.domain.chat.thread import Message, MessageId, Speaker

AT = datetime(2026, 9, 17, 9, 0, tzinfo=UTC)


def _said(speaker: Speaker, text: str, decision: dict[str, object] | None = None) -> Message:
    return Message(
        id=MessageId("msg_" + str(abs(hash(text)) % 10**8)),
        speaker=speaker,
        text=text,
        said_at=AT,
        decision=decision,
    )


def _asking(**over: object) -> Message:
    decision: dict[str, object] = {
        "kind": NEEDS,
        "workflow_id": "wfl_1",
        "title": "Create a Customer Type",
        "values": {},
        "missing": ["Customer Type", "customertype-customerType"],
        **over,
    }
    return _said(Speaker.ASSISTANT, "What should Customer Type be?", decision)


def test_the_last_thing_the_assistant_decided_is_the_whole_state() -> None:
    """No session and no row: an operator who answers two questions over five
    minutes does not depend on a process staying up, and a second browser
    reading the thread sees the same thing."""
    pending = pending_job([_said(Speaker.OPERATOR, "make one"), _asking()])

    assert pending is not None
    assert pending.workflow_id == "wfl_1"
    assert pending.asking_for == "Customer Type"
    assert question(pending) == "What should Customer Type be?"


def test_a_conversation_that_moved_on_is_not_waiting() -> None:
    """A job abandoned twenty minutes ago must not claim the next sentence
    somebody types. The newer decision is not a question, and that ends it."""
    moved = _said(Speaker.ASSISTANT, "239 suppliers", {"kind": "answer"})

    assert pending_job([_asking(), _said(Speaker.OPERATOR, "how many suppliers"), moved]) is None


def test_nothing_is_waiting_on_an_empty_conversation() -> None:
    assert pending_job([]) is None
    assert pending_job([_said(Speaker.OPERATOR, "hello")]) is None


def test_one_answer_fills_the_same_field_under_both_its_names() -> None:
    """`Create a Customer Type` declares each field twice -- the label a person
    reads and the body key a form posts -- and asking twice for one word is the
    form this conversation exists to replace.

    A patch over a mining defect, and deliberately a narrow one: it fills only
    names that ARE the asked name under another spelling.
    """
    pending = pending_job(
        [
            _asking(
                missing=[
                    "Customer Type",
                    "customertype-customerType",
                    "longDescription",
                ]
            )
        ]
    )
    assert pending is not None

    filled = answered(pending, "GPP")

    assert filled.values == {"Customer Type": "GPP", "customertype-customerType": "GPP"}
    assert filled.missing == ("longDescription",), "it answered a field nobody asked about"
    assert not filled.ready


def test_the_last_answer_makes_it_ready() -> None:
    pending = Pending(
        workflow_id="wfl_1", title="t", values={"a": "1"}, missing=("longDescription",)
    )

    filled = answered(pending, "type 03")

    assert filled.ready
    assert filled.values == {"a": "1", "longDescription": "type 03"}


def test_a_refusal_is_not_a_value() -> None:
    """Without this, "no" becomes the customer type."""
    assert let_go("no")
    assert let_go("  Never mind. ")
    # And a value that merely contains one of those words is a value: a run
    # refused because a description said "leave it in receiving" is worse than
    # one question too many.
    assert not let_go("leave it in receiving")
    assert not let_go("NORTH DOCK")


def test_a_blank_answer_changes_nothing() -> None:
    """A press of return is not an answer, and must not fill the field with
    "" -- a typed blank is refused at the door, so the job would die holding a
    value nobody gave."""
    pending = Pending(workflow_id="wfl_1", title="t", values={}, missing=("Customer Type",))

    assert answered(pending, "   ") == pending


def test_a_value_the_box_will_not_take_is_as_outstanding_as_one_nobody_gave() -> None:
    """More so, because the person believes they have already answered it.

    Measured on the deployment 2026-09-18: a mail carrying a ten-character code
    for a four-character field had nothing MISSING, so the offer read as ready
    and the door asked nothing on the one press it exists to answer.
    """
    limits = {"Customer Type": 4, "Description": 28}

    assert unusable({"Customer Type": "NEWSROTEST"}, limits) == ("Customer Type",)
    # Exactly what the box takes is not too long for it.
    assert unusable({"Customer Type": "NSRO"}, limits) == ()
    assert unusable({"Customer Type": "NSROT"}, limits) == ("Customer Type",)
    # A name nothing has measured is not judged, and a blank is missing rather
    # than unusable -- `missing` already names it.
    assert unusable({"Something Else": "x" * 90}, limits) == ()
    assert unusable({"Customer Type": ""}, limits) == ()


def test_what_is_outstanding_keeps_the_order_it_was_given_in() -> None:
    """The sentence a person reads asks for a code then a description every
    time, rather than in whatever order a dict happened to iterate."""
    limits = {"Customer Type": 4, "Description": 3}
    values = {"Customer Type": "NEWSROTEST", "Description": "north dock"}

    assert unusable(values, limits) == ("Customer Type", "Description")


def test_where_the_run_stopped_survives_the_answer_and_the_row() -> None:
    """A run that comes up short ENDS, and the answer starts another one. At
    step 0 that one re-walks everything the first performed -- re-opens the
    mail, re-navigates, presses Add again -- to arrive back at the box it
    stopped in front of."""
    waiting = Pending(
        workflow_id="wfl_1",
        title="Create a Customer Type",
        values={},
        missing=("Customer Type", "Description"),
        from_step=4,
    )

    # It survives an answer that does not finish the job...
    assert answered(waiting, "NSRO").from_step == 4
    # ...and the one that does.
    assert answered(answered(waiting, "NSRO"), "north dock").from_step == 4


def test_a_step_a_row_cannot_be_read_as_is_the_start_of_the_job() -> None:
    """A bool is an int in Python, so `from_step: true` would otherwise resume
    a job at its second step -- and a negative is a row nothing wrote."""
    said: object
    for said in (None, "4", True, False, -1, {}):
        assert _step(said) == 0, said
    assert _step(4) == 4
