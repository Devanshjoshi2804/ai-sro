"""One box, two worlds: whether a sentence wants an answer or an action.

The rule is words and no model, and what is held here is the shape of its
mistakes rather than a claim that it has none. Two failures matter in
different amounts: a question read as a job comes back "no job matched" and
costs a sentence; an instruction read as a question leaves the operator
waiting for something that is never going to happen.
"""

from __future__ import annotations

import pytest

from sro.domain.lookup.asking import is_a_question


@pytest.mark.parametrize(
    "said",
    [
        "which suppliers are set up at SG",
        "how many transport modes are there",
        "where do I see the work areas",
        "is the SG site live yet",
        "any open purchase orders for acme",
        "find the supplier called WMSupplier",
        "check whether that customer type exists",
        "show me the work areas at SG",
        "list the clients on this site",
        "status of the inbound shipment",
        "the supplier list for SG?",
        "please check the supplier list",
        "could you find out how many suppliers there are",
    ],
)
def test_a_sentence_that_wants_an_answer(said: str) -> None:
    assert is_a_question(said)


@pytest.mark.parametrize(
    "said",
    [
        "create a supplier called WMSupplier",
        "add demo values",
        "update the work area description",
        "delete the test customer type",
        "make a new client for acme",
        "run the depot job",
        "please add demo values",
        # The one that matters most: an instruction wearing a question's
        # punctuation. Read as a question, the operator waits for something
        # that is never going to happen.
        "can you add demo values?",
        "could you create a supplier for me?",
    ],
)
def test_a_sentence_that_wants_something_done(said: str) -> None:
    assert not is_a_question(said)


def test_a_tense_is_not_an_instruction() -> None:
    """`DOING` is matched on the first word only. "updated" inside a question
    about changed records is a tense, and a rule reading verbs anywhere sends
    every such question to the miner."""
    assert is_a_question("which suppliers were updated today")


def test_nothing_at_all_is_not_a_question() -> None:
    # The empty case belongs to whoever refuses empty input; this only has to
    # not claim it is a question.
    assert not is_a_question("   ")
