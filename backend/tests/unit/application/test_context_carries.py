"""A conversation whose every sentence is resolved alone is not a conversation.

An operator asked how many transport modes there are, was shown sixteen, and
then said "I want them viewed in detail" -- which was resolved from scratch,
matched nothing, and sent them to the knowledge base for a subject they had
just been shown.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.application.ports.intent import Reading
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.plan import NetworkPlan
from sro.domain.skill.skill import Skill
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.fakes import FakeEmbedder, FakeIntentParser, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


def _listing() -> Skill:
    skill = f.skill(
        name="List transport modes",
        versions=0,
        objective_key=f.objective(objective_type="list", entity_type="transport_mode"),
    )
    skill.add_version(
        f.skill_version(
            steps=(
                f.step(
                    index=0,
                    network_plan=NetworkPlan(
                        method="GET",
                        url=Template("https://wms.test/data/transportModes"),
                        expected_status=200,
                    ),
                ),
            ),
            parameters=(),
            summary="List every transport mode at SG",
            when_to_use="Use to answer questions about transport mode",
        )
    )
    return skill


def _creating() -> Skill:
    skill = f.skill(
        id=SkillId("skill-create"),
        name="Create",
        versions=0,
        objective_key=f.objective(objective_type="create", entity_type="transport_mode"),
    )
    skill.add_version(
        f.skill_version(
            steps=(
                f.step(
                    index=0,
                    network_plan=NetworkPlan(
                        method="POST",
                        url=Template("https://wms.test/data/transportModes"),
                        expected_status=201,
                    ),
                ),
            ),
            parameters=(),
            summary="Create transport mode at SG",
            when_to_use="Use to create transport mode",
        )
    )
    return skill


def _resolver(uow: FakeUnitOfWork) -> ResolveIntent:
    return ResolveIntent(uow, PlanTask(Retrieve(uow, FakeEmbedder())))


@pytest.mark.asyncio
async def test_a_follow_up_keeps_the_subject_of_the_question_before_it() -> None:
    uow = FakeUnitOfWork()
    async with uow:
        await uow.skills.add(_listing())
        await uow.commit()

    alone = await _resolver(uow).execute(CTX, utterance="i want them viewed in detail")
    carried = await _resolver(uow).execute(
        CTX,
        utterance="i want them viewed in detail",
        after="how many transport modes are in the list",
    )

    assert alone.matched is None
    assert carried.matched is not None
    assert carried.matched.skill.name == "List transport modes"


@pytest.mark.asyncio
async def test_the_subject_is_remembered_never_invented() -> None:
    """The follow-up still has to match something.

    Carrying context forward must not become "run whatever we ran last time"
    for a sentence about something else entirely.
    """
    uow = FakeUnitOfWork()
    async with uow:
        await uow.skills.add(_listing())
        await uow.commit()

    resolution = await _resolver(uow).execute(
        CTX, utterance="release the wave", after="how many transport modes are in the list"
    )

    assert resolution.matched is None


@pytest.mark.asyncio
async def test_the_answer_to_a_question_fills_the_skill_that_asked_it() -> None:
    """Asked for values, given values, and it kept the skill in hand.

    Resolved alone, "transport mode NEWTESTOFSRO and description made from
    chat" matched Create and List equally and offered a choice — so the
    operator picked the same skill again and lost what they had just typed.
    """
    uow = FakeUnitOfWork()
    creating = _creating()
    async with uow:
        await uow.skills.add(_listing())
        await uow.skills.add(creating)
        await uow.commit()

    resolution = await _resolver(uow).execute(
        CTX,
        utterance="transport mode NEWTESTOFSRO and description made from chat",
        pinned=creating.id.value,
    )

    assert resolution.matched is not None
    assert resolution.matched.skill.id == creating.id
    # And not offered as a choice: the skill under discussion is the one that
    # asked the question being answered, not one of several possibilities.
    assert "Which did you mean" not in (resolution.question or "")


@pytest.mark.asyncio
async def test_changing_your_mind_is_still_allowed() -> None:
    """A pinned skill must not swallow a sentence that plainly means something
    else. Answering a question with a new request is a thing people do."""
    uow = FakeUnitOfWork()
    creating = _creating()
    async with uow:
        await uow.skills.add(_listing())
        await uow.skills.add(creating)
        await uow.commit()

    resolution = await _resolver(uow).execute(
        CTX, utterance="list transport modes", pinned=creating.id.value
    )

    assert resolution.matched is not None
    assert resolution.matched.skill.name == "List transport modes"


@pytest.mark.asyncio
async def test_a_question_is_never_swallowed_by_a_skill_waiting_for_values() -> None:
    """What the operator saw: asked for a list, shown a create form. Twice.

    "How many transport modes are there, list them all" names no other task
    *confidently* — it never does, it is a question — so the create skill that
    was waiting for a code and a description answered it. Being asked something
    is the clearest signal that the previous question is over.
    """
    uow = FakeUnitOfWork()
    creating = _creating()
    async with uow:
        await uow.skills.add(_listing())
        await uow.skills.add(creating)
        await uow.commit()

    resolution = await _resolver(uow).execute(
        CTX,
        utterance="how many transport modes are there list them all",
        pinned=creating.id.value,
    )

    assert resolution.matched is not None
    assert resolution.matched.skill.name == "List transport modes"


@pytest.mark.asyncio
async def test_a_sentence_is_read_rather_than_pattern_matched() -> None:
    """The bug that ended the phrase lists.

    "Show the list of all transport_mode then" is a question by any reading. It
    began with no interrogative, ended with no question mark, and named no task
    confidently -- so every hand-written rule let the create skill that was
    waiting for values answer it, and the operator was shown a form again.
    """
    uow = FakeUnitOfWork()
    creating = _creating()
    async with uow:
        await uow.skills.add(_listing())
        await uow.skills.add(creating)
        await uow.commit()

    reader = FakeIntentParser(
        Reading(wants="ask", verb="list", entity="transport mode", confidence=0.9)
    )
    resolver = ResolveIntent(uow, PlanTask(Retrieve(uow, FakeEmbedder())), reader)

    resolution = await resolver.execute(
        CTX, utterance="show the list of all transport_mode then", pinned=creating.id.value
    )

    assert resolution.matched is not None
    assert resolution.matched.skill.name == "List transport modes"


@pytest.mark.asyncio
async def test_an_unsure_reading_is_not_used() -> None:
    """A model saying it does not know is more useful than one confidently
    wrong, so below the floor the words are matched literally -- which is what a
    deployment with no model does by construction."""
    uow = FakeUnitOfWork()
    creating = _creating()
    async with uow:
        await uow.skills.add(_listing())
        await uow.skills.add(creating)
        await uow.commit()

    reader = FakeIntentParser(
        Reading(wants="ask", verb="list", entity="transport mode", confidence=0.1)
    )
    resolver = ResolveIntent(uow, PlanTask(Retrieve(uow, FakeEmbedder())), reader)

    resolution = await resolver.execute(
        CTX, utterance="transport mode NEWONE and description something", pinned=creating.id.value
    )

    assert resolution.matched is not None
    assert resolution.matched.skill.id == creating.id
