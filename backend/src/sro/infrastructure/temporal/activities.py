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
from sro.domain.shared.identifiers import BrowserSessionId, PrincipalId, RecordingId, TenantId


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
