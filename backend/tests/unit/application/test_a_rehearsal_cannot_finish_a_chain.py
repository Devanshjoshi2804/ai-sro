"""A shadow run of a create chain, which by construction cannot complete.

Creating a client posts an address, then the client that names the address it
just made. Shadow withholds writes, so the address id is never minted -- and the
step that needs it was reported as a failed step, which made the run FAILED,
which meant a chained create could never earn its way off the first rung.

Nothing failed. The rehearsal did exactly what a rehearsal does, and stopped
where a rehearsal has to stop.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteStep, ExecutionRequest, StartRun
from sro.domain.execution.run import RunStatus, StepDisposition
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import Template
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
WMS = "https://wms.test/data/WM/wm"


async def _chain(uow: FakeUnitOfWork) -> None:
    """Post an address, then a client naming the address that came back."""
    skill = f.skill(versions=0)
    version = f.skill_version(
        steps=(
            f.step(
                index=0,
                network_plan=f.network_plan(
                    method="POST", url=Template(f"{WMS}/addresses"), body=Template("{}")
                ),
            ),
            f.step(
                index=1,
                network_plan=f.network_plan(
                    method="POST",
                    url=Template(f"{WMS}/clients"),
                    body=Template('{"addressId": "${address_id}"}'),
                ),
            ),
        ),
        parameters=(
            Parameter(
                name="address_id",
                kind=ParameterKind.DERIVED,
                source_step_index=0,
                source_pointer="/id",
            ),
        ),
    )
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)


async def test_a_withheld_write_leaves_the_next_step_withheld_not_failed() -> None:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await _chain(uow)
    run = await StartRun(uow, FakeClock(), FakeIdFactory()).execute(
        CTX, ExecutionRequest(skill_id=f.skill().id, parameters={})
    )
    assert run.stage is PromotionStage.SHADOW

    step = ExecuteStep(uow, http, vault)
    first = await step.execute(CTX, run_id=run.id, index=0)
    second = await step.execute(CTX, run_id=run.id, index=1)

    assert first.disposition is StepDisposition.WITHHELD
    assert second.disposition is StepDisposition.WITHHELD
    assert "address_id" in (second.detail or "")
    assert second.ok, "a rehearsal that stopped where rehearsals stop has not failed"


async def test_the_run_a_rehearsal_produces_is_a_clean_one() -> None:
    """Which is what lets a chained create earn its way to assisted at all."""
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await _chain(uow)
    run = await StartRun(uow, FakeClock(), FakeIdFactory()).execute(
        CTX, ExecutionRequest(skill_id=f.skill().id, parameters={})
    )
    step = ExecuteStep(uow, http, vault)
    await step.execute(CTX, run_id=run.id, index=0)
    await step.execute(CTX, run_id=run.id, index=1)

    run.finish(f.at(900))

    assert run.status is RunStatus.SUCCEEDED
    assert run.failure is None
