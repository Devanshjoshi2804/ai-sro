"""End a demonstration: sealed if it produced evidence, abandoned if not."""

from __future__ import annotations

from contextlib import suppress

from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserProvider, BrowserUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.recording.recording import Recording
from sro.domain.shared.identifiers import RecordingId


class FinishRecording:
    def __init__(self, uow: UnitOfWork, browser: BrowserProvider, clock: Clock) -> None:
        self._uow = uow
        self._browser = browser
        self._clock = clock

    async def seal(self, ctx: RequestContext, *, recording_id: RecordingId) -> Recording:
        return await self._finish(ctx, recording_id=recording_id, reason=None)

    async def abandon(
        self, ctx: RequestContext, *, recording_id: RecordingId, reason: str
    ) -> Recording:
        return await self._finish(ctx, recording_id=recording_id, reason=reason)

    async def _finish(
        self, ctx: RequestContext, *, recording_id: RecordingId, reason: str | None
    ) -> Recording:
        now = self._clock.now()

        async with self._uow as uow:
            recording = await uow.recordings.get(ctx.tenant_id, recording_id)
            if reason is None:
                recording.seal(now)
            else:
                recording.abandon(now, reason)
            await uow.recordings.save(recording)
            await uow.commit()

        if recording.browser_session_id is not None:
            # Best effort: the recording is already durable, and a provider
            # outage must not turn a good demonstration into a failed request.
            # The RecordingWorkflow reaper collects anything left behind.
            with suppress(BrowserUnavailable):
                await self._browser.close(recording.browser_session_id)

        return recording
