"""Getting a browser to work in, where the deployment has one.

Opening a second browser is the right thing to ask for and the wrong thing to
insist on: a self-hosted provider has exactly one, and asking while it is in use
does not produce another -- it produces a refusal, or worse, takes the screen
away from whatever was using it. So ask, and when the answer is no, use the one
that is open, unless somebody is demonstrating in it.
"""

from __future__ import annotations

from sro.application.ports.browser import BrowserProvider, BrowserSession, BrowserUnavailable
from sro.application.ports.repositories import UnitOfWork


async def a_browser(browser: BrowserProvider, uow: UnitOfWork) -> BrowserSession:
    """A new browser, or the one already open. Raises if there is neither."""
    try:
        return await browser.open()
    except BrowserUnavailable:
        async with uow as unit:
            capturing = await unit.recordings.list_capturing()
        # Never one somebody is demonstrating in: two things driving one screen
        # record each other's gestures, and the demonstration is the evidence
        # everything else is built from.
        taken = {str(recording.browser_session_id) for recording in capturing}
        for session_id in await browser.live_sessions():
            if str(session_id) in taken:
                continue
            return BrowserSession(
                id=session_id,
                live_view_url=await browser.live_view_url(session_id) or "",
                debugger_url=await browser.debugger_url(session_id),
            )
        raise
