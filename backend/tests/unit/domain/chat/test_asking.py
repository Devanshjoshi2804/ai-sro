"""What a conversation is waiting on, and what an answer does to it."""

from __future__ import annotations

from datetime import UTC, datetime

from sro.domain.chat.asking import (
    NEEDS,
    Pending,
    _step,
    answered,
    asking_state,
    asks,
    cannot_without,
    let_go,
    opening,
    pending_job,
    question,
    still_to_ask,
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


# --- what the job could ALSO set ---------------------------------------------


def _short_job(**over: object) -> Pending:
    return Pending(
        workflow_id="wfl_1",
        title="Create a Customer Type",
        values={"Customer Type": "NRT2"},
        missing=("Customer Type Description",),
        limits={"Customer Type Description": 2000},
        **over,
    )


def test_a_field_nobody_has_to_fill_is_offered_once_with_what_it_was() -> None:
    """Since 2026-09-22 an optional field no longer stops a run, and the step
    that fills it is skipped where nothing was given. Skipping it silently is
    the other half of the old mistake: a field the operator DID want goes
    unfilled and nothing says it was ever possible.

    Once, in the opening, and never as a question of its own -- four questions
    nobody has to answer is how a person learns to type "no" without reading.
    """
    said = opening(_short_job(offered=(("Department", "NOTHING"), ("Manufacturer", "NIGHTCO"))))

    assert "I can also set Department and Manufacturer" in said
    assert "last time Department: NOTHING; Manufacturer: NIGHTCO" in said
    assert "or I will run without" in said


def test_the_offer_comes_before_the_question_it_must_not_swallow() -> None:
    """The question is what the next sentence answers. A question buried above
    an offer gets the offer's answer."""
    said = opening(_short_job(offered=(("Department", "IN"),)))

    assert said.index("I can also set") < said.index("What should it be?")


def test_a_job_with_nothing_optional_says_nothing_about_it() -> None:
    said = opening(_short_job())

    assert "I can also set" not in said


def test_an_offer_nobody_has_a_last_value_for_is_still_made() -> None:
    """A field this job has never filled is still one it can fill. The offer
    simply has nothing to suggest."""
    said = opening(_short_job(offered=(("Pallet Building", ""),)))

    assert "I can also set Pallet Building" in said
    assert "last time" not in said


def test_three_offered_fields_read_as_a_list_and_not_as_two() -> None:
    """A comma before the last is how a list of two reads as a list of three."""
    said = opening(_short_job(offered=(("A", ""), ("B", ""), ("C", ""))))

    assert "I can also set A, B and C" in said


def test_the_offer_survives_the_thread_it_was_written_into() -> None:
    """The state is the thread. A second browser reading it offers the same
    fields, and an answer arriving minutes later is still an answer to this."""
    asked = Message(
        id=MessageId("m1"),
        speaker=Speaker.ASSISTANT,
        text="...",
        said_at=datetime(2026, 9, 22, 3, 0, tzinfo=UTC),
        decision={
            "kind": NEEDS,
            "workflow_id": "wfl_1",
            "missing": ["Customer Type Description"],
            "offered": [["Department", "NOTHING"], ["Manufacturer", "NIGHTCO"]],
        },
    )

    waiting = pending_job([asked])

    assert waiting is not None
    assert waiting.offered == (("Department", "NOTHING"), ("Manufacturer", "NIGHTCO"))


def test_an_offer_stored_in_a_shape_nobody_wrote_is_no_offer() -> None:
    """An offer read out of the wrong shape is an offer to fill a field that
    may not exist."""
    for bad in ("Department", [["Department"]], [{"name": "Department"}], None, 7):
        asked = Message(
            id=MessageId("m1"),
            speaker=Speaker.ASSISTANT,
            text="...",
            said_at=datetime(2026, 9, 22, 3, 0, tzinfo=UTC),
            decision={
                "kind": NEEDS,
                "workflow_id": "wfl_1",
                "missing": ["Customer Type"],
                "offered": bad,
            },
        )

        waiting = pending_job([asked])

        assert waiting is not None and waiting.offered == (), f"{bad!r} became an offer"


# --- F1: one question for everything required, and "don't have X" is final --


def _both(**over: object) -> Pending:
    fields: dict[str, object] = {
        "workflow_id": "wfl_1",
        "title": "Create a Customer Type",
        "values": {},
        "missing": ("Customer Type", "Customer Type Description"),
        "limits": {"Customer Type": 4},
        "options": {"Customer Type Description": ("RETAIL", "B2B")},
        **over,
    }
    return Pending(**fields)


def test_every_required_field_is_asked_for_in_one_question_with_its_limits_and_options() -> None:
    """greyorange QA: 44% of assistant turns asked for one value at a time."""
    said = question(_both())

    assert said.count("?") == 1, said
    assert "What should Customer Type and Customer Type Description be?" in said
    assert "Customer Type takes 4 characters" in said
    assert "Customer Type Description is one of RETAIL, B2B" in said
    assert asks(_both()) == [
        {"name": "Customer Type", "max_length": 4, "options": []},
        {"name": "Customer Type Description", "max_length": None, "options": ["RETAIL", "B2B"]},
    ]


def test_an_optional_field_is_never_asked_for() -> None:
    """Offered once, in the opening, as a list; never in the question."""
    pending = _both(offered=(("Department", ""), ("Manufacturer", "OUTSIDE")))

    assert "Department" not in question(pending)
    assert "Manufacturer" not in question(pending)
    assert [one["name"] for one in asks(pending)] == ["Customer Type", "Customer Type Description"]


def test_two_required_fields_are_answered_in_one_reply() -> None:
    filled = answered(_both(), "Customer Type: RRF, Customer Type Description: B2B")

    assert filled.values == {"Customer Type": "RRF", "Customer Type Description": "B2B"}
    assert filled.ready


def test_each_value_in_one_reply_is_read_with_its_own_checks() -> None:
    """R1's checks by the answer's natural unit: the bad value is dropped and
    the good one kept, and only what is still missing is asked again."""
    filled = answered(_both(), "customer type :- RRF; Customer Type Description = WHOLESALE")

    assert filled.values == {"Customer Type": "RRF"}
    assert filled.missing == ("Customer Type Description",)
    assert filled.refused == {"Customer Type Description": "not one of RETAIL, B2B"}
    assert question(filled).startswith("Customer Type Description is one of RETAIL, B2B")


def test_an_offered_field_may_be_filled_in_the_same_reply() -> None:
    pending = _both(missing=("Customer Type",), options={}, offered=(("Department", "IN"),))

    filled = answered(pending, "Customer Type: RRF and Department: D1")

    assert filled.values == {"Customer Type": "RRF", "Department": "D1"}
    assert filled.ready and filled.offered == ()


def test_thr_c563_department_then_manufacturer_is_not_had_and_never_asked_again() -> None:
    """thr_c563: "i dont have manufature just run whatever we have", and the
    assistant asked for Manufacturer again."""
    pending = _both(
        missing=("Customer Type",),
        options={},
        offered=(("Department", ""), ("Manufacturer", "OUTSIDE")),
    )

    first = answered(pending, "Department: D1")
    assert first.values == {"Department": "D1"}
    assert first.missing == ("Customer Type",)
    assert "Manufacturer" not in question(first) and "Department" not in question(first)

    last = answered(first, "Customer Type: RRF. i dont have manufature just run whatever we have")

    assert last.values == {"Department": "D1", "Customer Type": "RRF"}
    assert last.dropped == ("Manufacturer",)
    assert last.ready and last.offered == ()
    assert last.without == ()


def test_a_field_said_not_to_be_had_is_dropped_by_its_misspelt_name() -> None:
    pending = _both(missing=("Customer Type",), offered=(("Manufacturer", ""),))

    for said in ("i dont have manufature", "skip Manufacturer", "run without the manufacturer"):
        filled = answered(pending, said)
        assert filled.dropped == ("Manufacturer",), said
        assert filled.values == {} and filled.missing == ("Customer Type",), said


def test_a_value_that_merely_mentions_skipping_is_a_value() -> None:
    pending = _both(missing=("Customer Type Description",), options={})

    filled = answered(pending, "skip the queue at dock 4")

    assert filled.values == {"Customer Type Description": "skip the queue at dock 4"}
    assert filled.dropped == ()


def test_a_required_field_that_is_not_had_ends_the_ask_with_a_note() -> None:
    filled = answered(_both(), "we don't have a customer type description")

    assert filled.without == ("Customer Type Description",)
    assert not filled.ready
    said, decision = cannot_without(filled)
    assert "cannot run without Customer Type Description" in said
    assert "?" not in said, "the note is not another question"
    assert decision["kind"] != NEEDS
    assert decision["dropped"] == ["Customer Type Description"]


def test_what_was_dropped_rides_the_thread_and_is_never_asked_again_there() -> None:
    dropped = Message(
        id=MessageId("m1"),
        speaker=Speaker.ASSISTANT,
        text="...",
        said_at=AT,
        decision={
            "kind": "job",
            "workflow_id": "wfl_1",
            "dropped": ["Manufacturer", "Customer Type Description"],
            "offered": [["Department", ""]],
        },
    )
    other = Message(
        id=MessageId("m2"),
        speaker=Speaker.ASSISTANT,
        text="...",
        said_at=AT,
        decision={"kind": NEEDS, "workflow_id": "wfl_2", "dropped": ["Customer Type"]},
    )
    fresh = _both(offered=(("Department", ""), ("Manufacturer", ""), ("Pallet", "")))

    again = still_to_ask(fresh, [dropped, other])

    assert again.missing == ("Customer Type",), "another job's drop is not this job's"
    assert again.without == ("Customer Type Description",)
    assert again.offered == (("Pallet", ""),), "offered once in a thread, and never a dropped one"
    assert set(again.dropped) == {"Manufacturer", "Customer Type Description"}


def test_the_drop_survives_the_thread_it_was_written_into() -> None:
    asked = _said(
        Speaker.ASSISTANT,
        "What should Customer Type be?",
        {
            "kind": NEEDS,
            "workflow_id": "wfl_1",
            "missing": ["Customer Type"],
            "dropped": ["Manufacturer"],
            "options": {"Customer Type": ["GT1", "GT2"], "bad": "GT3"},
        },
    )

    waiting = pending_job([asked])

    assert waiting is not None
    assert waiting.dropped == ("Manufacturer",)
    assert waiting.options == {"Customer Type": ("GT1", "GT2")}
    assert asking_state(waiting) == {
        "asks": [{"name": "Customer Type", "max_length": None, "options": ["GT1", "GT2"]}],
        "dropped": ["Manufacturer"],
        "options": {"Customer Type": ["GT1", "GT2"]},
    }
