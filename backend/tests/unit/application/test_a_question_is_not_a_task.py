"""Asking how many there are must never offer to create one.

Found by asking the console both sentences about the first task ever taught.
"Create a transport mode called SROTEST9" matched correctly and pulled both
values out of the sentence. "How many transport modes are in the list" matched
the *same* skill -- the one that creates them -- and answered by asking which
transport mode to create.

Every noun agrees. Only the shape of the sentence disagrees, and it is the only
thing that matters: one asks to be told something, the other asks for something
to be done, and they are not two points on one scale.
"""

from __future__ import annotations

import pytest

from sro.application.intent.match import asks, rank, writes
from sro.domain.skill.plan import Template
from sro.domain.skill.skill import Skill
from tests import factories as f


def _skill(name: str, *, method: str, objective_type: str, entity: str) -> Skill:
    built = f.skill(
        name=name,
        versions=0,
        objective_key=f.objective(objective_type=objective_type, entity_type=entity),
    )
    built.add_version(
        f.skill_version(
            steps=(
                f.step(
                    index=0,
                    network_plan=f.network_plan(
                        method=method,
                        url=Template(f"https://wms.test/data/{entity}"),
                        body=None,
                    ),
                ),
            ),
            summary=f"{objective_type} {entity} at SG",
            when_to_use=f"Use to {objective_type} {entity}",
        )
    )
    return built


@pytest.mark.parametrize(
    "sentence",
    [
        "how many transport modes are in the list",
        "How many transport modes are there?",
        "which transport modes exist",
        "list all transport modes",
        "are there transport modes at SG",
    ],
)
def test_a_question_never_matches_a_skill_that_writes(sentence: str) -> None:
    creating = _skill("Create", method="POST", objective_type="create", entity="transport_mode")

    assert rank((creating,), sentence) == ()


@pytest.mark.parametrize(
    "sentence",
    [
        "create a transport mode called SROTEST9",
        "add a transport mode",
        # No question mark, no interrogative opening: an instruction, and the
        # safe direction to be wrong in is treating it as one.
        "create transport mode and tell me how many exist",
    ],
)
def test_an_instruction_still_reaches_the_skill_that_does_it(sentence: str) -> None:
    creating = _skill("Create", method="POST", objective_type="create", entity="transport_mode")

    assert rank((creating,), sentence)


def test_a_question_still_matches_a_skill_that_only_reads() -> None:
    """The rule is about writing, not about questions.

    Once somebody demonstrates looking the list up, that skill answers this.
    """
    listing = _skill("List", method="GET", objective_type="list", entity="transport_mode")

    assert rank((listing,), "how many transport modes are in the list")


def test_the_shape_of_a_sentence_is_read_from_how_it_opens() -> None:
    assert asks("how many are there")
    assert asks("Anything at all?")
    # "count" reads like a question and is one of the most consequential tasks
    # in a warehouse. "show" appears in "show me how to create one".
    assert not asks("count the inventory in SG")
    assert not asks("show me how to create a transport mode")


def test_writing_is_read_from_the_plan_not_from_the_name() -> None:
    reading = _skill("Anything", method="GET", objective_type="list", entity="x")
    writing = _skill("Anything", method="POST", objective_type="list", entity="x")

    assert not writes(reading.versions[-1])
    assert writes(writing.versions[-1])


def test_a_skill_that_explains_the_verb_and_not_the_subject_is_not_a_candidate() -> None:
    """ "give me list of clients" offered List suppliers, List addresses and List
    transport modes -- three answers about the wrong thing, matched on the word
    "list" alone. One structural hit clears the floor, and the matcher had
    already recorded "clients" as a word it could not explain."""
    library = (
        _skill("List suppliers at SG", method="GET", objective_type="list", entity="supplier"),
        _skill("List addresses at SG", method="GET", objective_type="list", entity="address"),
    )

    offered = rank(library, "give me list of clients", question=True, entity="client")

    assert offered == ()


def test_the_subject_still_matches_the_skill_that_is_about_it() -> None:
    library = (
        _skill("List suppliers at SG", method="GET", objective_type="list", entity="supplier"),
        _skill("List addresses at SG", method="GET", objective_type="list", entity="address"),
    )

    offered = rank(library, "give me list of suppliers", question=True, entity="supplier")

    assert [c.skill.name for c in offered] == ["List suppliers at SG"]


def test_a_subject_nobody_read_changes_nothing() -> None:
    """Without a confident reading there is no subject to insist on, and the
    matcher behaves exactly as it did."""
    library = (
        _skill("List suppliers at SG", method="GET", objective_type="list", entity="supplier"),
    )

    assert len(rank(library, "give me list of clients", question=True)) == 1
