"""The limits, where they are enforced: before anything has been sent."""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import (
    ExecuteSkill,
    ExecutionRequest,
    Refused,
    StartRun,
)
from sro.domain.execution.run import Run, RunId
from sro.domain.execution.safety import TRIP_AFTER
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillVersion
from sro.domain.skill.track_record import DEMOTE_AFTER_FAILURES
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
SYSTEM = "blue_yonder"


async def _skill(
    uow: FakeUnitOfWork, stage: PromotionStage = PromotionStage.ASSISTED
) -> SkillVersion:
    version = f.skill_version()
    skill = f.skill(versions=0, objective_key=f.objective(target_system=SYSTEM))
    skill.add_version(version)
    current = PromotionStage.RECORDED
    while current is not stage:
        current = current.next_stage()
        version.promote(current, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)
    return version


async def _failed_runs(uow: FakeUnitOfWork, how_many: int) -> None:
    for index in range(how_many):
        run = Run(
            id=RunId(f"old-{index}"),
            tenant_id=f.TENANT,
            skill_id=SkillId("skill-1"),
            skill_version=1,
            stage=PromotionStage.ASSISTED,
            parameters={},
            requested_by=f.OPERATOR,
            started_at=f.at(800),
            authorized_by=f.OPERATOR,
            target_system=SYSTEM,
        )
        run.fail(f.at(900), "the system answered 500")
        await uow.runs.add(run)


async def test_a_system_that_keeps_failing_stops_being_asked() -> None:
    """Retrying into a degraded WMS is how an outage becomes an incident."""
    uow, http = FakeUnitOfWork(), FakeHttpCaller()
    await _skill(uow)
    await _failed_runs(uow, TRIP_AFTER)

    with pytest.raises(Refused, match="a person should look"):
        await StartRun(uow, FakeClock(), FakeIdFactory()).execute(
            CTX,
            ExecutionRequest(
                skill_id=SkillId("skill-1"),
                parameters={"shipment_id": "1"},
                authorized_by="supervisor",
            ),
        )

    assert http.sent == [], "the breaker is checked before anything is sent"


async def test_a_run_records_which_system_it_touched() -> None:
    uow = FakeUnitOfWork()
    await _skill(uow)

    run = await StartRun(uow, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "1"},
            authorized_by="supervisor",
        ),
    )

    assert run.target_system == SYSTEM, "the breaker asks about a system, not a skill"


async def test_a_clean_run_advances_the_version_s_case_for_autonomy() -> None:
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    http = FakeHttpCaller()
    http.answer(status_code=200, text='{"ok": true}')
    version = await _skill(uow)

    await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "1"},
            authorized_by="supervisor",
        ),
    )

    assert version.track_record.clean_streak == 1
    assert version.track_record.total_runs == 1


async def test_a_skill_that_keeps_failing_demotes_itself() -> None:
    """Nobody is asked. Confirming a few runs costs minutes; a broken
    autonomous skill keeps writing."""
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    version = await _skill(uow)

    for index in range(DEMOTE_AFTER_FAILURES):
        http = FakeHttpCaller()
        http.answer(status_code=500, text="{}")
        ids = FakeIdFactory()
        for _ in range(index):
            ids.new_run_id()  # a fresh id per run
        await ExecuteSkill(uow, http, vault, FakeClock(), ids).execute(
            CTX,
            ExecutionRequest(
                skill_id=SkillId("skill-1"),
                parameters={"shipment_id": "1"},
                authorized_by="supervisor",
            ),
        )

    assert version.track_record.consecutive_failures >= DEMOTE_AFTER_FAILURES
    assert version.stage is PromotionStage.SHADOW
    assert "failed in a row" in (version.demotion_reason or "")


async def test_a_withheld_shadow_run_changes_no_counter() -> None:
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    http = FakeHttpCaller()
    http.answer(status_code=200, text="{}")
    version = await _skill(uow, PromotionStage.SHADOW)

    await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
        CTX, ExecutionRequest(skill_id=SkillId("skill-1"), parameters={"shipment_id": "1"})
    )

    assert version.track_record.total_runs == 0, "a rehearsal proves nothing about the system"
