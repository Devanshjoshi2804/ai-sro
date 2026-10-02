"""A skill whose work lands in one system after passing through another.

"Check the WMS, then record it in the ERP" is one job and can never be one
candidate -- an episode breaks on a host change. When somebody says those two
candidates are one piece of work, what comes out is an ordinary skill with one
extra fact on it: every system it touches.

That fact exists for the circuit breaker. A run is keyed by where the work
lands, so a workflow failing in its *second* system would be stored under the
first and never trip the second's breaker. Asking every breaker while answering
for only one is half a breaker, and half a breaker reads exactly like a whole
one until an incident.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import (
    ExecuteSkill,
    ExecutionRequest,
    Refused,
)
from sro.domain.execution.run import Run, RunId
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import DeviceId, SkillId
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f
from tests.unit.fakes import (
    FakeAgentDrivers,
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
WMS, ERP = "blue_yonder", "sap"


async def _skill(uow: FakeUnitOfWork, *, systems: tuple[str, ...], keyed: str = WMS) -> None:
    version = f.skill_version(steps=(f.step(),), systems=systems)
    skill = f.skill(versions=0, objective_key=f.objective(target_system=keyed))
    skill.add_version(version)
    for stage in (PromotionStage.SHADOW, PromotionStage.ASSISTED):
        version.promote(stage, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)


def _run(uow: FakeUnitOfWork, *, systems: tuple[str, ...], ident: str) -> Run:
    run = Run(
        id=RunId(ident),
        tenant_id=f.TENANT,
        skill_id=SkillId("skill-1"),
        skill_version=1,
        stage=PromotionStage.ASSISTED,
        parameters={},
        requested_by=f.OPERATOR,
        started_at=f.at(800),
        authorized_by=f.OPERATOR,
        target_system=WMS,
        systems=systems,
    )
    run.fail(f.at(900), "the system answered 500")
    return run


def _executor(uow: FakeUnitOfWork, agents: FakeAgentDrivers | None = None) -> ExecuteSkill:
    return ExecuteSkill(
        uow,
        FakeHttpCaller(),
        FakeCredentialVault(),
        FakeClock(),
        FakeIdFactory(),
        agents=agents,
        servers={},
    )


async def test_a_run_of_it_records_every_system_it_touches() -> None:
    uow = FakeUnitOfWork()
    await _skill(uow, systems=(WMS, ERP))

    run = await _executor(uow, FakeAgentDrivers()).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
            device_id=DeviceId("dev-1"),
        ),
    )

    assert run.systems == (WMS, ERP)
    # And still keyed by where the work lands, which is what everything else
    # reads.
    assert run.target_system == WMS


async def test_it_will_not_run_without_a_browser_signed_in_to_both() -> None:
    """This deployment holds one session per system and never two at once.

    Refused before anything happens rather than discovered at step four, with
    the first system already written to and no way to authenticate the second.
    """
    uow = FakeUnitOfWork()
    await _skill(uow, systems=(WMS, ERP))

    with pytest.raises(DomainError, match="signed in to all of them"):
        await _executor(uow).execute(
            CTX,
            ExecutionRequest(
                skill_id=SkillId("skill-1"),
                parameters={"shipment_id": "555"},
                authorized_by="supervisor",
            ),
        )


async def test_an_ordinary_skill_still_runs_without_one() -> None:
    """One system is every skill there has ever been, and none of them needs a
    device."""
    uow = FakeUnitOfWork()
    await _skill(uow, systems=(WMS,))

    run = await _executor(uow).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    assert run.device_id is None


async def test_a_workflow_s_failures_reach_the_breaker_of_the_system_it_damaged() -> None:
    """The whole reason a run records more than one system.

    Three workflows have failed. Each is keyed by the WMS, because that is where
    its work lands — but each also wrote into the ERP on the way. An ordinary
    ERP skill must now be refused: something has been failing against the ERP
    repeatedly, and the fact that it was keyed elsewhere does not make the ERP
    any healthier.

    Without `Run.systems` those three runs are invisible here, and the ERP's
    breaker protects it from single-system runs only — while the thing actually
    damaging it goes free.
    """
    uow = FakeUnitOfWork()
    await _skill(uow, systems=(ERP,), keyed=ERP)
    for index in range(3):
        await uow.runs.add(_run(uow, systems=(WMS, ERP), ident=f"old-{index}"))

    with pytest.raises(Refused, match="a person should look"):
        await _executor(uow).execute(
            CTX,
            ExecutionRequest(
                skill_id=SkillId("skill-1"),
                parameters={"shipment_id": "555"},
                authorized_by="supervisor",
            ),
        )


async def test_a_single_system_skill_is_not_stopped_by_another_system() -> None:
    """The other half of the same rule: `systems` widens what a breaker sees,
    and must not widen what it stops."""
    uow = FakeUnitOfWork()
    await _skill(uow, systems=(ERP,), keyed=ERP)
    for index in range(3):
        # Keyed by the WMS and touching nothing else: an ERP skill is no
        # business of theirs.
        await uow.runs.add(_run(uow, systems=(), ident=f"old-{index}"))

    run = await _executor(uow).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"shipment_id": "555"},
            authorized_by="supervisor",
        ),
    )

    assert run.id is not None
