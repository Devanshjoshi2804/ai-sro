"""Chat: what was asked, what it was taken to mean, and what was not done."""

from __future__ import annotations

from sro.application.chat.converse import Converse, StartThread
from sro.application.context import RequestContext
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.domain.chat.thread import Speaker
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeEmbedder, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


async def _taught(uow: FakeUnitOfWork) -> None:
    skill = f.skill(
        id=SkillId("skill-adjust"),
        name="Inventory Adjust",
        objective_key=f.objective(objective_type="adjust", entity_type="inventory", facility="SG"),
        versions=0,
    )
    version = f.skill_version()
    version.describe(summary="Adjust inventory at SG.", when_to_use="After a stock check.")
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(600), f.OPERATOR)
    await uow.skills.add(skill)


def _chat(uow: FakeUnitOfWork) -> tuple[StartThread, Converse]:
    ids, clock = FakeIdFactory(), FakeClock()
    resolver = ResolveIntent(uow, PlanTask(Retrieve(uow, FakeEmbedder())))
    return StartThread(uow, clock, ids), Converse(uow, resolver, clock, ids)


async def test_a_thread_keeps_what_was_asked_and_what_was_decided() -> None:
    uow = FakeUnitOfWork()
    await _taught(uow)
    start, converse = _chat(uow)
    thread = await start.execute(CTX)

    thread = await converse.execute(
        CTX, thread_id=thread.id, text="adjust inventory at SG", parameters={"shipment_id": "1"}
    )

    operator, assistant = thread.messages
    assert operator.speaker is Speaker.OPERATOR and operator.text == "adjust inventory at SG"
    assert assistant.speaker is Speaker.ASSISTANT
    assert "Inventory Adjust" in assistant.text
    assert assistant.decision["matched_skill_id"] == "skill-adjust"
    assert assistant.decision["why"], "the audit trail reads the decision, not the prose"


async def test_saying_something_performs_nothing() -> None:
    """A match is an offer. Starting it is the operator's next request, which is
    what makes their confirmation the authorisation an assisted run records."""
    uow = FakeUnitOfWork()
    await _taught(uow)
    start, converse = _chat(uow)
    thread = await start.execute(CTX)

    await converse.execute(CTX, thread_id=thread.id, text="adjust inventory at SG")

    assert uow.runs.rows == {}


async def test_what_is_still_needed_is_asked_for_in_the_reply() -> None:
    uow = FakeUnitOfWork()
    await _taught(uow)
    start, converse = _chat(uow)
    thread = await start.execute(CTX)

    thread = await converse.execute(CTX, thread_id=thread.id, text="adjust inventory at SG")

    assert "I need shipment_id" in thread.messages[-1].text
    assert thread.messages[-1].decision["missing_parameters"] == ["shipment_id"]


async def test_an_unknown_task_is_answered_with_a_way_forward() -> None:
    uow = FakeUnitOfWork()
    start, converse = _chat(uow)
    thread = await start.execute(CTX)

    thread = await converse.execute(CTX, thread_id=thread.id, text="do something else entirely")

    assert "Teach me" in thread.messages[-1].text
    assert thread.messages[-1].decision["matched_skill_id"] is None


async def test_a_thread_is_titled_by_what_was_asked_first() -> None:
    uow = FakeUnitOfWork()
    await _taught(uow)
    start, converse = _chat(uow)
    thread = await start.execute(CTX)

    thread = await converse.execute(CTX, thread_id=thread.id, text="adjust inventory at SG")
    thread = await converse.execute(CTX, thread_id=thread.id, text="and again tomorrow")

    assert thread.title == "adjust inventory at SG"
    assert len(thread.messages) == 4, "nothing is edited; everything is appended"
