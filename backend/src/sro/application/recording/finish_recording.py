from __future__ import annotations

from contextlib import suppress

from sro.application.capture.identity import derive_objective_key, system_of
from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserProvider, BrowserUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.recording.recording import Recording
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import RecordingId
from sro.domain.shared.objective import ObjectiveKey


class UnnamedDemonstration(InvariantViolation):
    code = "unnamed_demonstration"


def _urls_seen(recording: Recording) -> tuple[str, ...]:
    return tuple(
        frame.primary_request.url for frame in recording.frames if frame.primary_request is not None
    )


class FinishRecording:
    def __init__(self, uow: UnitOfWork, browser: BrowserProvider, clock: Clock) -> None:
        self._uow = uow
        self._browser = browser
        self._clock = clock

    async def seal(
        self,
        ctx: RequestContext,
        *,
        recording_id: RecordingId,
        objective_key: ObjectiveKey | None = None,
    ) -> Recording:
        return await self._finish(
            ctx, recording_id=recording_id, reason=None, objective_key=objective_key
        )

    async def abandon(
        self, ctx: RequestContext, *, recording_id: RecordingId, reason: str
    ) -> Recording:
        return await self._finish(ctx, recording_id=recording_id, reason=reason)

    async def _finish(
        self,
        ctx: RequestContext,
        *,
        recording_id: RecordingId,
        reason: str | None,
        objective_key: ObjectiveKey | None = None,
    ) -> Recording:
        now = self._clock.now()

        async with self._uow as uow:
            recording = await uow.recordings.get(ctx.tenant_id, recording_id)
            if reason is None:
                if recording.objective_key is None:
                    connections = await uow.connections.list_for_tenant(ctx.tenant_id)
                    named = objective_key or derive_objective_key(
                        recording.frames,
                        system=system_of(connections, *_urls_seen(recording)),
                    )
                    if named is None:
                        raise UnnamedDemonstration(
                            "this demonstration made no call that says what it was; "
                            "name the task to seal it"
                        )
                    recording.name_objective(named)
                recording.seal(now)
            else:
                recording.abandon(now, reason)
            await uow.recordings.save(recording)
            await uow.commit()

        if recording.browser_session_id is not None:
            with suppress(BrowserUnavailable):
                await self._browser.close(recording.browser_session_id)

        return recording
