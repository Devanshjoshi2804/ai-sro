"""Work that must survive a process dying.

Two very different needs behind one port:

- **Induction** is a computation whose inputs are already durable. Running it
  through a workflow buys retries and a history to look at when it fails, not
  correctness.
- **The session deadline** is the opposite: nothing else in the system will ever
  notice that an operator walked away, so if this is not durable the recording
  stays open forever.
"""

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
        second: RecordingId,
        name: str | None = None,
    ) -> InducedSkill:
        """Run induction durably and wait for its result."""
        ...

    async def execute_skill(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        version: int | None = None,
        authorized_by: str | None = None,
    ) -> RunId:
        """Perform a skill durably and wait for it to finish.

        Durable for a different reason again: a run touches a live warehouse one
        step at a time, and a process that dies halfway must be resumable
        without repeating the step that may already have landed.
        """
        ...

    async def watch_recording(
        self,
        ctx: RequestContext,
        *,
        recording_id: RecordingId,
        browser_session_id: BrowserSessionId,
        timeout_seconds: int,
    ) -> bool:
        """Start the deadline that reaps this demonstration if it is abandoned.

        Returns whether the watch was actually started. Best effort by contract:
        the recording is already durable by the time this is called, so a
        scheduler outage must cost a deadline, never the demonstration.
        """
        ...

    async def recording_finished(self, ctx: RequestContext, *, recording_id: RecordingId) -> None:
        """Tell the deadline it is no longer needed. Never raises."""
        ...
