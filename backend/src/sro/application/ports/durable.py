from __future__ import annotations

from typing import Protocol

from sro.application.context import RequestContext
from sro.application.induction.induce_skill import InducedSkill
from sro.domain.execution.run import RunId
from sro.domain.shared.identifiers import BrowserSessionId, RecordingId, SkillId


class DurableExecution(Protocol):
    async def induce_skill(
        self,
        ctx: RequestContext,
        *,
        first: RecordingId,
        second: RecordingId | None = None,
        name: str | None = None,
    ) -> InducedSkill: ...

    async def execute_skill(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        version: int | None = None,
        authorized_by: str | None = None,
        medium: str = "network",
        run_id: RunId | None = None,
        wait: bool = True,
    ) -> RunId: ...

    async def watch_recording(
        self,
        ctx: RequestContext,
        *,
        recording_id: RecordingId,
        browser_session_id: BrowserSessionId,
        timeout_seconds: int,
    ) -> bool: ...

    async def recording_finished(
        self, ctx: RequestContext, *, recording_id: RecordingId
    ) -> None: ...
