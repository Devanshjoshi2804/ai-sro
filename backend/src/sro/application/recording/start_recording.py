"""Open a browser session and the Recording that will collect its frames."""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserProvider
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.recording.recording import Recording
from sro.domain.shared.identifiers import BrowserSessionId, RecordingId
from sro.domain.shared.objective import ObjectiveKey


@dataclass(frozen=True, slots=True)
class StartedRecording:
    recording_id: RecordingId
    live_view_url: str

    debugger_url: str = ""
    """CDP endpoint for the capture adapter. Never put on the wire."""

    browser_session_id: BrowserSessionId | None = None


class StartRecording:
    def __init__(
        self,
        uow: UnitOfWork,
        browser: BrowserProvider,
        clock: Clock,
        ids: IdFactory,
    ) -> None:
        self._uow = uow
        self._browser = browser
        self._clock = clock
        self._ids = ids

    async def execute(
        self,
        ctx: RequestContext,
        *,
        objective_key: ObjectiveKey,
        start_url: str | None = None,
        label: str | None = None,
    ) -> StartedRecording:
        # Browser first: if it fails nothing is written, so we never accumulate
        # recordings that can only ever be abandoned.
        session = await self._browser.open(start_url=start_url)

        recording = Recording(
            id=self._ids.new_recording_id(),
            tenant_id=ctx.tenant_id,
            objective_key=objective_key,
            demonstrator=ctx.principal_id,
            started_at=self._clock.now(),
            label=label,
        )
        recording.attach_browser_session(session.id)

        async with self._uow as uow:
            await uow.recordings.add(recording)
            await uow.commit()

        return StartedRecording(
            recording_id=recording.id,
            live_view_url=session.live_view_url,
            debugger_url=session.debugger_url,
            browser_session_id=session.id,
        )
