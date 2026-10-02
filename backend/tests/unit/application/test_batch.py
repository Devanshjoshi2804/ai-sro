"""Doing one taught task to several things.

A batch is N runs, not a new kind of execution: one item failing says nothing
about the others, and a safety limit stops the batch rather than the item.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.batch import RunBatch
from sro.application.execution.execute_skill import ExecuteSkill
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


async def _skill(uow: FakeUnitOfWork) -> None:
    version = f.skill_version()
    skill = f.skill(versions=0)
    skill.add_version(version)
    for stage in (PromotionStage.SHADOW, PromotionStage.ASSISTED):
        version.promote(stage, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)


def _batch(uow: FakeUnitOfWork, http: FakeHttpCaller) -> RunBatch:
    return RunBatch(
        ExecuteSkill(uow, http, FakeCredentialVault(), FakeClock(), FakeIdFactory(), servers={})
    )


async def test_each_item_is_its_own_run_with_its_own_record() -> None:
    uow, http = FakeUnitOfWork(), FakeHttpCaller()
    await _skill(uow)
    for _ in range(3):
        http.answer(status_code=200, text='{"ok": true}')

    result = await _batch(uow, http).execute(
        CTX,
        skill_id=SkillId("skill-1"),
        items=({"shipment_id": "1"}, {"shipment_id": "2"}, {"shipment_id": "3"}),
        authorized_by="supervisor",
    )

    assert result.performed == 3
    assert len({item.run.id for item in result.items if item.run}) == 3


async def test_an_item_missing_a_value_does_not_stop_the_others() -> None:
    uow, http = FakeUnitOfWork(), FakeHttpCaller()
    await _skill(uow)
    http.answer(status_code=200, text="{}")

    result = await _batch(uow, http).execute(
        CTX,
        skill_id=SkillId("skill-1"),
        items=({}, {"shipment_id": "2"}),
        authorized_by="supervisor",
    )

    assert result.items[0].refused and "no value supplied" in result.items[0].refused
    assert result.items[1].succeeded
    assert result.stopped_early is None


async def test_a_failing_system_stops_the_batch_rather_than_the_item() -> None:
    """A WMS that started answering 500 does not need the remaining forty."""
    uow, http = FakeUnitOfWork(), FakeHttpCaller()
    await _skill(uow)
    for _ in range(12):
        http.answer(status_code=500, text="{}")

    result = await _batch(uow, http).execute(
        CTX,
        skill_id=SkillId("skill-1"),
        items=tuple({"shipment_id": str(n)} for n in range(10)),
        authorized_by="supervisor",
    )

    assert result.stopped_early is not None
    assert len(result.items) < 10, "the rest were never attempted"
