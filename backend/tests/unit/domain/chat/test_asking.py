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
    named_in,
    opening,
    pending_job,
    question,
    still_to_ask,
    turned_down,
    unusable,
)
from sro.domain.chat.request import Candidate
from sro.domain.chat.thread import Message, MessageId, Speaker
from sro.domain.execution.field_classes import FieldClass, FieldLimits

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
        "missing": ["Customer Type"],
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


# --- F1 round 1: only an explicit drop, only a field that is plainly meant ---


def _waiting(*missing: str, offered: tuple[str, ...] = (), **over: object) -> Pending:
    fields: dict[str, object] = {
        "workflow_id": "wfl_1",
        "title": "Create a Customer Type",
        "values": {},
        "missing": missing,
        "offered": tuple((name, "") for name in offered),
        **over,
    }
    return Pending(**fields)


def test_c1_a_sentence_that_is_not_an_explicit_drop_drops_nothing() -> None:
    pending = _waiting("Customer Type", offered=("Department", "Manufacturer"))

    for said in (
        "let me check what we have",
        "also check what I have in stock for SKU 12",
        "I don't know the department yet",
        "skip it",
        "not yet",
    ):
        assert answered(pending, said).dropped == (), said
        assert not named_in(pending, said), f"{said!r} was kept from the reader"
    # A holding reply is not a value either: the field stays asked.
    for said in ("let me check what we have", "I don't know the department yet", "skip it"):
        filled = answered(pending, said)
        assert filled.missing == ("Customer Type",) and filled.values == {}, said


def test_c1_each_explicit_drop_phrase_drops_the_field_it_names() -> None:
    pending = _waiting("Customer Type", offered=("Manufacturer",))

    for said in (
        "don't have manufacturer",
        "we do not have the manufacturer",
        "skip Manufacturer",
        "run without manufacturer",
    ):
        assert answered(pending, said).dropped == ("Manufacturer",), said
    assert set(answered(pending, "just run with what we have").dropped) == {
        "Customer Type",
        "Manufacturer",
    }


def test_c2_an_exact_name_wins_over_a_near_one() -> None:
    pending = _waiting("Customer Type", "Customer Tier")

    assert answered(pending, "don't have customer tier").dropped == ("Customer Tier",)


def test_c2_a_near_name_one_word_away_is_never_that_field() -> None:
    pending = _waiting("Ship To Code")

    assert answered(pending, "skip ship from code").dropped == ()
    filled = answered(pending, "Ship From Code: SG1")
    assert filled.values == {} and filled.missing == ("Ship To Code",)


def test_c2_a_word_of_a_name_is_not_the_name_and_asks_which_was_meant() -> None:
    pending = _waiting("Zip Code", "Ship To Code")

    dropped = answered(pending, "don't have code")
    assert dropped.dropped == () and dropped.missing == ("Zip Code", "Ship To Code")
    assert dropped.which == {"code": ("Zip Code", "Ship To Code")}
    assert 'which field "code" is: Zip Code or Ship To Code' in turned_down(dropped)

    one = answered(_waiting("Zip Code"), "Code: 123")
    assert one.values == {}, "a word of the name filled the field"
    assert one.which == {"Code": ("Zip Code",)}


def test_c2_a_misspelt_name_is_that_field_only_when_nothing_else_comes_close() -> None:
    assert answered(
        _waiting("Customer Type", offered=("Manufacturer",)), "i dont have manufature"
    ).dropped == ("Manufacturer",)
    tied = _waiting("Customer Type", "Customer Typo")
    assert answered(tied, "skip customer typ").dropped == (), "a tie was settled by guessing"
    assert answered(tied, "skip customer typ").which == {
        "customer typ": ("Customer Type", "Customer Typo")
    } or answered(tied, "skip customer typ").which == {
        "customer typ": ("Customer Typo", "Customer Type")
    }


def test_c3_an_unlabelled_reply_to_two_fields_is_not_taken() -> None:
    pending = _waiting("Customer Type", "Customer Type Description")

    filled = answered(pending, "RRF")

    assert filled.values == {} and filled.missing == pending.missing
    assert filled.which == {"RRF": ("Customer Type", "Customer Type Description")}
    assert "Customer Type: …; Customer Type Description: …" in question(filled)


def test_c3_unless_it_is_an_option_of_exactly_one_of_them() -> None:
    pending = _waiting(
        "Customer Type", "Customer Type Description", options={"Customer Type": ("GT1", "GT2")}
    )

    assert answered(pending, "gt2").values == {"Customer Type": "gt2"}
    both = _waiting("A", "B", options={"A": ("X",), "B": ("X",)})
    assert answered(both, "X").values == {}


def test_c3_one_field_missing_still_takes_the_bare_reply() -> None:
    assert answered(_waiting("Customer Type"), "RRF").values == {"Customer Type": "RRF"}


def test_i1_a_name_the_job_knows_it_by_is_that_field() -> None:
    known = Candidate(
        id="wfl_1",
        title="Create a Customer Type",
        fields=(
            FieldClass("Customer Type", "required", ("Customer Type", "Type Code"), FieldLimits()),
            FieldClass("Manufacturer", "sometimes", ("Manufacturer",), FieldLimits()),
        ),
        aliases={"maker": "Manufacturer"},
        seen={},
    )
    pending = _waiting("Customer Type", offered=("Manufacturer",), known=known)

    filled = answered(pending, "Type Code: RRF, don't have maker")

    assert filled.values == {"Customer Type": "RRF"}
    assert filled.dropped == ("Manufacturer",)


def test_i2_a_named_value_ends_at_its_clause() -> None:
    pending = _waiting("Customer Type", offered=("Manufacturer", "Discount"))

    one = answered(pending, "Customer Type: RRF i dont have manufacturer")
    assert one.values == {"Customer Type": "RRF"} and one.dropped == ("Manufacturer",)

    two = answered(pending, "Customer Type: RRF, create it without discount")
    assert two.values == {"Customer Type": "RRF"} and two.dropped == ("Discount",)


def test_m3_a_label_inside_a_value_is_part_of_the_value() -> None:
    pending = _waiting("Customer Type Description", offered=("Customer Type",))

    filled = answered(pending, "Customer Type Description: returns for Customer Type: B2B")

    assert filled.values == {"Customer Type Description": "returns for Customer Type: B2B"}


def test_m1_values_given_with_a_required_drop_are_kept_on_the_note() -> None:
    pending = _waiting("Customer Type", "Customer Type Description")

    filled = answered(pending, "Customer Type: RRF, don't have customer type description")

    assert filled.without == ("Customer Type Description",)
    said, decision = cannot_without(filled)
    assert decision["values"] == {"Customer Type": "RRF"}
    assert "ask for Create a Customer Type again" in said


def _resumed(values: dict[str, str], dropped: list[str]) -> Message:
    return _said(
        Speaker.ASSISTANT,
        "Running Create a Customer Type now.",
        {
            "kind": "job",
            "workflow_id": "wfl_1",
            "values": values,
            "resume": True,
            "dropped": dropped,
        },
    )


def test_i3_a_drop_holds_for_the_run_its_own_answer_started_and_no_other() -> None:
    later = _waiting("Customer Type", offered=("Manufacturer",), values={"Customer Type": "RRFX"})

    same = still_to_ask(later, [_resumed({"Customer Type": "RRFX"}, ["Manufacturer"])])
    assert same.dropped == ("Manufacturer",) and same.offered == ()

    fresh = still_to_ask(later, [_resumed({"Customer Type": "GT1"}, ["Manufacturer"])])
    assert fresh == later, "a new start inherited an earlier ask's drop"
    moved_on = still_to_ask(
        later,
        [
            _resumed({"Customer Type": "RRFX"}, ["Manufacturer"]),
            _said(Speaker.ASSISTANT, "...", {"kind": "job", "workflow_id": "wfl_1"}),
        ],
    )
    assert moved_on == later


# --- F1 round 2: a named value is never cut silently --------------------------


def test_9_a_value_runs_on_until_a_clause_that_starts_something_of_this_ask() -> None:
    for name, said, value in (
        ("Description", "Description: black and white", "black and white"),
        ("Address", "Address: 12 Main St, Springfield", "12 Main St, Springfield"),
        ("Address", "Address: 5 St. Louis Ave", "5 St. Louis Ave"),
        (
            "Description",
            "Description: Retail, wholesale and export",
            "Retail, wholesale and export",
        ),
    ):
        filled = answered(_waiting(name, "Customer Type"), said)
        assert filled.values == {name: value}, said


def test_9_a_drop_word_inside_a_value_that_names_no_field_is_part_of_the_value() -> None:
    pending = _waiting("Description", "Customer Type", offered=("Discount",))

    filled = answered(pending, "Description: sold without labels")

    assert filled.values == {"Description": "sold without labels"}
    assert filled.dropped == ()


def test_10a_a_skip_inside_a_value_naming_a_field_is_asked_about_once() -> None:
    pending = _waiting("Description", "Customer Type", offered=("Discount",))

    asked = answered(pending, "Description: sold without discount")

    assert asked.values == {} and asked.dropped == (), "written silently either way"
    assert asked.missing == ("Description", "Customer Type")
    assert "Did you mean to skip Discount, or is it part of the value?" in turned_down(asked)
    assert asking_state(asked)["doubted"] == ["Discount"]

    again = answered(asked, "Description: sold without discount")

    assert again.values == {"Description": "sold without discount"}, "asked twice"
    assert again.dropped == ()


def test_9_the_next_label_of_this_ask_still_ends_a_value() -> None:
    pending = _waiting("Customer Type", "Customer Type Description")

    filled = answered(pending, "Customer Type: GGD; Customer Type Description: black and white")

    assert filled.values == {
        "Customer Type": "GGD",
        "Customer Type Description": "black and white",
    }


def test_12_a_label_that_is_no_field_is_part_of_the_one_value_asked_for() -> None:
    for said in ("Name: SROCL01", "Attn: Bob, 5 Main St", "Note: fragile", "Re: order 55"):
        filled = answered(_waiting("Address"), said)
        assert filled.values == {"Address": said}, said
        assert filled.which == {}, said


def test_12_a_label_that_names_another_field_of_the_job_is_asked_about() -> None:
    known = Candidate(
        id="wfl_1",
        title="Create a Customer Type",
        fields=(
            FieldClass("Address", "required", ("Address",), FieldLimits()),
            FieldClass("Department", "sometimes", ("Department",), FieldLimits()),
        ),
        aliases={},
        seen={},
    )

    filled = answered(_waiting("Address", known=known), "Department: IN")

    assert filled.values == {} and "Department" in filled.which


def test_13_not_having_it_yet_is_not_ready_and_the_field_stays_asked() -> None:
    pending = _waiting("Customer Type", offered=("Department",))

    for said in ("I don't have the department yet", "i dont have the department for now"):
        filled = answered(pending, said)
        assert filled.dropped == (), said
        assert filled.offered == (("Department", ""),), said
        assert filled.values == {} and filled.missing == ("Customer Type",), said


# --- F1 round 3: a clause _read would act on is never joined onto a value ----


def test_7_a_not_ready_clause_ends_the_value_and_leaves_its_field_asked() -> None:
    pending = _waiting("Customer Type", offered=("Manufacturer",))

    filled = answered(pending, "Customer Type: RRF, i don't have manufacturer yet")

    assert filled.values == {"Customer Type": "RRF"}
    assert filled.dropped == () and filled.offered == (("Manufacturer", ""),)


def test_8_a_label_of_a_field_already_given_ends_the_value() -> None:
    known = Candidate(
        id="wfl_1",
        title="Create a Customer Type",
        fields=(
            FieldClass("Customer Type", "required", ("Customer Type",), FieldLimits()),
            FieldClass("Department", "sometimes", ("Department",), FieldLimits()),
        ),
        aliases={},
        seen={},
    )
    pending = _waiting("Customer Type", values={"Department": "IN"}, known=known)

    filled = answered(pending, "Customer Type: GGD, Department: IN")

    assert filled.values == {"Department": "IN", "Customer Type": "GGD"}


def test_9_a_label_asked_about_ends_the_value_and_is_asked_about() -> None:
    zipped = answered(_waiting("Customer Type", "Zip Code"), "Customer Type: GGD, Code: 123")
    assert zipped.values == {"Customer Type": "GGD"}
    assert zipped.which == {"Code": ("Zip Code",)}

    short = answered(_waiting("Customer Type", "Description"), "Customer Type: GGD, Desc: first")
    assert short.values == {"Customer Type": "GGD"}
    assert short.which == {"Desc": ("Description",)}
