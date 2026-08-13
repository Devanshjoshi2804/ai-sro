"""Open a browser session and the Recording that will collect its frames."""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserProvider, BrowserSession
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


def _external_browser(debugger_url: str) -> BrowserSession:
    """A browser the operator already has open, attached over CDP.

    Teaching in the operator's own browser rather than a hosted one is not a
    fallback: they see the real thing at full size, with their extensions,
    printers and certificates, and there is no video stream between them and the
    work. What we give up is being able to reopen the session later without
    them, which is what a hosted session is for.

    The provider does not own this browser, so the session id says so — closing
    it is not ours to do.
    """
    return BrowserSession(
        id=BrowserSessionId("attached"),
        live_view_url="",
        debugger_url=debugger_url,
    )


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
        attach_to: str | None = None,
    ) -> StartedRecording:
        # Browser first: if it fails nothing is written, so we never accumulate
        # recordings that can only ever be abandoned.
        session = (
            _external_browser(attach_to)
            if attach_to
            else await self._browser.open(start_url=start_url)
        )

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
