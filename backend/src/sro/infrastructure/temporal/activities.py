"""Activities: the effectful half. Everything that touches the world lives here.

Arguments and returns are plain dataclasses because Temporal serialises them.
Domain objects stay behind the use case, so a change to an aggregate never
invalidates a workflow history.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from temporalio import activity

from sro.application.context import RequestContext

if TYPE_CHECKING:
    # Type-only: the composition root builds the activities, so importing it at
    # runtime would make anything that schedules work import every adapter.
    from sro.container import Container
from sro.application.execution.execute_skill import ExecutionRequest
from sro.domain.execution.run import Medium, RunId
from sro.domain.shared.identifiers import (
    BrowserSessionId,
    PrincipalId,
    RecordingId,
    SkillId,
    TenantId,
)


@dataclass
class InductionRequest:
    tenant_id: str
    principal_id: str
    first_recording_id: str
    second_recording_id: str
    name: str | None = None


@dataclass
class InductionResult:
    skill_id: str
    version: int
    step_count: int
    input_parameter_count: int
    derived_parameter_count: int


@dataclass
class StartRunRequest:
    tenant_id: str
    principal_id: str
    skill_id: str
    parameters: dict[str, str]
    version: int | None = None
    authorized_by: str | None = None
    medium: str = "network"


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
    """Whether this step changed the target system. The workflow uses it to
    decide that a failure must not be retried."""


@dataclass
class ReapRequest:
    tenant_id: str
    recording_id: str
    browser_session_id: str


class Activities:
    """Bound to a container so the worker owns exactly one set of adapters."""

    def __init__(self, container: Container) -> None:
        self._container = container

    @activity.defn(name="induce_skill")
    async def induce_skill(self, request: InductionRequest) -> InductionResult:
        ctx = RequestContext(
            tenant_id=TenantId(request.tenant_id),
            principal_id=PrincipalId(request.principal_id),
        )
        induced = await self._container.induce_skill().execute(
            ctx,
            first=RecordingId(request.first_recording_id),
            second=RecordingId(request.second_recording_id),
            name=request.name,
        )
        return InductionResult(
            skill_id=induced.skill_id.value,
            version=induced.version,
            step_count=induced.step_count,
            input_parameter_count=induced.input_parameter_count,
            derived_parameter_count=induced.derived_parameter_count,
        )

    @activity.defn(name="abandon_stale_recording")
    async def abandon_stale_recording(self, request: ReapRequest) -> bool:
        """Close a demonstration nobody came back to.

        Returns whether anything was abandoned, so the workflow can say what it
        did rather than report success either way.
        """
        ctx = RequestContext(
            tenant_id=TenantId(request.tenant_id),
            principal_id=PrincipalId("system"),
        )
        uow = self._container.unit_of_work()
        async with uow as unit:
            recording = await unit.recordings.get(ctx.tenant_id, RecordingId(request.recording_id))
            if not recording.is_open:
                return False

        await self._container.finish_recording().abandon(
            ctx,
            recording_id=RecordingId(request.recording_id),
            reason="session timed out without being finished",
        )
        return True

    @activity.defn(name="close_browser_session")
    async def close_browser_session(self, session_id: str) -> None:
        await self._container.browser.close(BrowserSessionId(session_id))

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
        outcome = await self._container.execute_step().execute(
            ctx, run_id=RunId(request.run_id), index=request.index
        )
        return StepResult(
            index=outcome.index,
            disposition=outcome.disposition.value,
            ok=outcome.ok,
            mutating=outcome.idempotency_key is not None,
        )

    @activity.defn(name="finish_run")
    async def finish_run(self, request: StepRequest) -> str:
        ctx = _context(request.tenant_id, request.principal_id)
        run = await self._container.finish_run().execute(ctx, run_id=RunId(request.run_id))
        return run.status.value


def _context(tenant_id: str, principal_id: str) -> RequestContext:
    return RequestContext(tenant_id=TenantId(tenant_id), principal_id=PrincipalId(principal_id))
