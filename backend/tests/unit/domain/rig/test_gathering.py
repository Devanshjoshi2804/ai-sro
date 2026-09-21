"""What a gather may decide, and what it must drop.

The pure half. The loop's stopping rules are held here so they can be checked
without a model or a mailbox, and because every one of them is a place a gather
could quietly put a model's reading of somebody's mail into a warehouse write.
"""

from __future__ import annotations

import json

from sro.domain.execution.gathering import (
    K_BODY,
    K_HIT,
    K_NOTE,
    Found,
    Gathered,
    keep,
    note,
    still_wanted,
)

CODE, DESCRIPTION = "Customer Type", "Customer Type Description"


def _found(value: str, message: str = "msg-1") -> Found:
    return Found(value=value, from_message=message, quoting=f"…{value}…")


def test_what_is_still_wanted_is_asked_in_the_order_the_job_declares() -> None:
    """A job that declares a code and a description says them in that order
    every time. The alternative is a sentence to a person that reshuffles
    itself between runs for no reason they can see."""
    assert still_wanted([CODE, DESCRIPTION], {}) == (CODE, DESCRIPTION)
    assert still_wanted([CODE, DESCRIPTION], {CODE: _found("ZQ50")}) == (DESCRIPTION,)
    assert still_wanted([CODE, DESCRIPTION], {CODE: _found("a"), DESCRIPTION: _found("b")}) == ()


def test_a_value_with_no_message_behind_it_is_not_a_value() -> None:
    """The whole rule this carries provenance for. A value the model could not
    point at a message for is a value it produced rather than read, and a
    warehouse write is the last place that belongs."""
    said = {CODE: Found(value="ZQ50", from_message="")}

    assert keep(said, [CODE]) == {}


def test_a_value_for_a_parameter_this_job_never_declared_is_dropped() -> None:
    """A model asked for two values and offering a third has read the mail for
    something nobody asked about. Dropped rather than refused: the two it was
    asked for may be perfectly good."""
    said = {CODE: _found("ZQ50"), "Warehouse": _found("SG")}

    assert set(keep(said, [CODE, DESCRIPTION])) == {CODE}


def test_a_blank_value_is_nobody_answering() -> None:
    """The same rule `typed_values` keeps: a parameter answered with an empty
    string is a parameter nobody answered, and sending it would put a blank in
    a required field rather than stopping to ask."""
    assert keep({CODE: _found("")}, [CODE]) == {}
    assert keep({CODE: _found("   ")}, [CODE]) == {}


def test_a_gather_that_found_nothing_says_so_rather_than_looking_complete() -> None:
    """`complete` is what a caller branches on, so an empty gather must not
    read as a satisfied one."""
    nothing = Gathered(missing=(CODE, DESCRIPTION))
    everything = Gathered(values={CODE: _found("ZQ50")})

    assert not nothing.complete
    assert everything.complete


def test_history_is_a_note_and_never_the_mail() -> None:
    """The mitigation the loop's failure modes ask for. What the next round
    needs is "this search found three messages", not four screens of somebody's
    mail -- raw accumulation is how a loop poisons, distracts and confuses
    itself."""
    said = note("search 'customer type'", "x" * (K_NOTE * 3))

    assert said.startswith("search 'customer type' -> ")
    assert len(said) < K_NOTE * 2
    assert said.endswith("…")


def test_a_note_is_one_line_however_the_mailbox_wrapped_it() -> None:
    """A body arrives with newlines and runs of spaces, and a history entry
    that spans lines makes every later prompt a different shape."""
    said = note("read msg-1", "a\n\n   b\tc")

    assert said == "read msg-1 -> a b c"


def test_every_hit_in_a_search_reaches_the_round_that_could_read_it() -> None:
    """The defect measured on the deployment 2026-09-16.

    `search_threads` answered with five threads and a flat 240-character cut
    kept the first one, mid-snippet. The four ids behind it were never shown to
    the round whose only way forward was to read one of them -- so it said
    `done` with nothing, and "the mailbox does not hold this" was a statement
    about the prompt again.

    A body is one thing and is trimmed as one. A list is trimmed row by row.
    """
    said = note(
        "search 'customer type'",
        json.dumps(
            {
                "messages": [
                    {"id": f"m-{n}", "subject": "Fwd: Create a customer TYPE", "snippet": "x" * 400}
                    for n in range(5)
                ]
            }
        ),
    )

    assert [f"m-{n}" in said for n in range(5)] == [True] * 5
    # And no hit arrived whole: five untrimmed rows would be four screens of
    # mail, which is the accumulation the note exists to prevent.
    assert all(len(row) < K_HIT * 2 for row in said.split(" | "))


def test_a_search_that_found_nothing_says_so_in_words() -> None:
    """`{"messages": []}` is a shape, not a sentence. The round that reads it
    has to be able to tell an empty mailbox from a mailbox it never reached."""
    assert note("search 'customer type'", '{"messages": []}').endswith("no messages")


def test_a_message_that_was_read_keeps_enough_of_itself_to_quote_from() -> None:
    """The one call whose whole point is the text a value is quoted out of.

    A request that opens with a greeting and a line of context has spent 240
    characters before it says the code, so `K_NOTE` would cut the answer off
    exactly where the value is.
    """
    body = "Hi team, " + ("context " * 40) + "the code is ZQ50."
    said = note("read m-1", json.dumps({"id": "m-1", "body": body}))

    assert "the code is ZQ50." in said
    assert len(said) < K_BODY * 2
