"""Where a demonstration happens, when the deployment has one browser.

Connecting a system opens the browser and leaves it open while the operator
signs in. The very next thing they do is teach -- and teaching asked for a
second browser, was refused, and told them to restart the container. The browser
they were looking at, signed in, on the right screen, was the one thing that
could not be used.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserSession, BrowserUnavailable
from sro.application.recording.start_recording import StartRecording
from tests import factories as f
from tests.unit.fakes import FakeBrowserProvider, FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


class _OneBrowser(FakeBrowserProvider):
    """Refuses a second session, exactly as a self-hosted Steel does."""

    async def open(self, *, start_url: str | None = None) -> BrowserSession:
        if [held for held in self.opened if held not in self.closed]:
            raise BrowserUnavailable("this deployment has one browser and it is already in use")
        return await super().open(start_url=start_url)


async def test_teaching_uses_the_browser_that_is_already_open() -> None:
    uow, browser = FakeUnitOfWork(), _OneBrowser()
    already = await browser.open()

    started = await StartRecording(uow, browser, FakeClock(), FakeIdFactory()).execute(
        CTX, label="run 1"
    )

    assert started.browser_session_id == already.id
    assert started.debugger_url, "and it is attachable, or capture has nothing to watch"


async def test_a_browser_somebody_is_demonstrating_in_is_never_taken() -> None:
    """Two recordings capturing one screen record each other's gestures."""
    uow, browser = FakeUnitOfWork(), _OneBrowser()
    theirs = await browser.open()
    recording = f.recording()
    recording.attach_browser_session(theirs.id)
    await uow.recordings.add(recording)

    with pytest.raises(BrowserUnavailable):
        await StartRecording(uow, browser, FakeClock(), FakeIdFactory()).execute(CTX, label="run 1")
