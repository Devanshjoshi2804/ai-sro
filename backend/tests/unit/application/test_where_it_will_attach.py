"""Which browser a recording may be attached to.

``attach_to`` is a debugger URL taken from the request body and dialled by the
backend, with a scripting engine on the far end. Unbounded it reaches anything
the backend can reach -- another container, an internal service, a cloud
metadata endpoint -- on nothing but a caller's say-so. The browser being
attached to is the operator's own, which is on this machine.
"""

from __future__ import annotations

import pytest

from sro.application.connection.browsers import Browsers
from sro.application.context import RequestContext
from sro.application.recording.start_recording import BrowserNotAttachable, StartRecording
from tests import factories as f
from tests.unit.fakes import FakeBrowserProvider, FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
LOOPBACK = ("127.0.0.1", "localhost")


def _teaching(hosts: tuple[str, ...] = LOOPBACK) -> StartRecording:
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    return StartRecording(
        uow,
        browser,
        clock,
        FakeIdFactory(),
        Browsers(browser, uow, clock, FakeIdFactory()),
        hosts,
    )


async def test_the_operator_s_own_chrome_is_attachable() -> None:
    started = await _teaching().execute(
        CTX, label="run 1", attach_to="ws://127.0.0.1:9222/devtools/browser/abc"
    )

    assert started.browser_session_id is not None


@pytest.mark.parametrize(
    "attach_to",
    [
        "ws://169.254.169.254/latest/meta-data/",
        "http://steel.internal:9223/devtools/browser/abc",
        "ws://127.0.0.1.evil.test:9222/devtools/browser/abc",
    ],
)
async def test_a_debugger_somewhere_else_is_refused(attach_to: str) -> None:
    with pytest.raises(BrowserNotAttachable):
        await _teaching().execute(CTX, label="run 1", attach_to=attach_to)


async def test_a_url_that_is_not_a_debugger_endpoint_is_refused() -> None:
    """The scheme matters as much as the host: a URL library will open
    ``file:`` on our behalf without complaining."""
    with pytest.raises(BrowserNotAttachable):
        await _teaching().execute(CTX, label="run 1", attach_to="file:///etc/passwd")
