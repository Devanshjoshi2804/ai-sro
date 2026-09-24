from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from temporalio import activity

from sro.application.context import RequestContext

if TYPE_CHECKING:
    from sro.container import Container
from sro.application.execution.execute_skill import ExecutionRequest
from sro.domain.execution.run import Medium, RunId
from sro.domain.shared.identifiers import (
    PrincipalId,
    SkillId,
    TenantId,
    TriggerId,
)


@dataclass
class StartRunRequest:
    tenant_id: str
    principal_id: str
    skill_id: str
    parameters: dict[str, str]
    version: int | None = None
    authorized_by: str | None = None
    medium: str = "network"
    run_id: str = ""


@dataclass
class StartedRun:
    run_id: str
    step_count: int


@dataclass
class StepRequest:
    tenant_id: str
    principal_id: str
    run_id: str
    index: int


@dataclass
class StepResult:
    index: int
    disposition: str
    ok: bool
    mutating: bool

    more: bool = False


@dataclass
class TriggerRequest:
    trigger_id: str


@dataclass
class TriggerResult:
    trigger_id: str
    run_id: str | None
    skipped: str | None


class Activities:
    def __init__(self, container: Container) -> None:
        self._container = container

    @activity.defn(name="start_run")
    async def start_run(self, request: StartRunRequest) -> StartedRun:
        ctx = _context(request.tenant_id, request.principal_id)
        run = await self._container.start_run().execute(
            ctx,
            ExecutionRequest(
                skill_id=SkillId(request.skill_id),
                parameters=dict(request.parameters),
                version=request.version,
                authorized_by=request.authorized_by,
                medium=Medium(request.medium),
                run_id=RunId(request.run_id) if request.run_id else None,
            ),
        )
        uow = self._container.unit_of_work()
        async with uow as unit:
            skill = await unit.skills.get(ctx.tenant_id, run.skill_id)
        return StartedRun(
            run_id=run.id.value,
            step_count=len(skill.version(run.skill_version).steps),
        )

    @activity.defn(name="execute_step")
    async def execute_step(self, request: StepRequest) -> StepResult:
        ctx = _context(request.tenant_id, request.principal_id)
        step = self._container.execute_step()
        outcome = await step.execute(ctx, run_id=RunId(request.run_id), index=request.index)
        return StepResult(
            index=outcome.index,
            disposition=outcome.disposition.value,
            ok=outcome.ok,
            mutating=outcome.idempotency_key is not None,
            more=await step.has_more(ctx, run_id=RunId(request.run_id)),
        )

    @activity.defn(name="finish_run")
    async def finish_run(self, request: StepRequest) -> str:
        ctx = _context(request.tenant_id, request.principal_id)
        run = await self._container.finish_run().execute(ctx, run_id=RunId(request.run_id))
        return run.status.value

    @activity.defn(name="fire_trigger")
    async def fire_trigger(self, request: TriggerRequest) -> TriggerResult:
        fired = await self._container.fire_trigger().execute(TriggerId(request.trigger_id))
        return TriggerResult(
            trigger_id=fired.trigger_id.value,
            run_id=fired.run_id.value if fired.run_id else None,
            skipped=fired.skipped,
        )


def _context(tenant_id: str, principal_id: str) -> RequestContext:
    return RequestContext(tenant_id=TenantId(tenant_id), principal_id=PrincipalId(principal_id))
