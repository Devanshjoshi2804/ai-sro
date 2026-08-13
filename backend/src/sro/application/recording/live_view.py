"""Where to point an operator at a demonstration in progress."""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserProvider, BrowserUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.domain.shared.identifiers import RecordingId


class GetLiveView:
    """Asks the provider rather than reading a stored URL.

    A live view belongs to a browser session, not to a recording: it stops
    existing when the session ends, and a URL kept on the row would go stale
    without anything noticing.
    """

    def __init__(self, uow: UnitOfWork, browser: BrowserProvider) -> None:
        self._uow = uow
        self._browser = browser

    async def execute(self, ctx: RequestContext, *, recording_id: RecordingId) -> str | None:
        async with self._uow as uow:
            recording = await uow.recordings.get(ctx.tenant_id, recording_id)

        if not recording.is_open or recording.browser_session_id is None:
            return None
        try:
            return await self._browser.live_view_url(recording.browser_session_id)
        except BrowserUnavailable:
            # The demonstration is still valid; only the window into it is gone.
            return None
