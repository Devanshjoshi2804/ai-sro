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
from sro.domain.skill.plan import NetworkPlan
from sro.domain.skill.skill import Skill
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.fakes import FakeEmbedder, FakeUnitOfWork

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
