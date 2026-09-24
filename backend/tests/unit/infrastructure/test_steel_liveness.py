"""A session with no browser behind it is not a session.

Every case here was observed on the real thing. Steel's Chrome died leaving a
stale singleton lock; the session stayed marked live forever; releasing it
answered 200 and changed nothing; and because a self-hosted Steel has exactly
one browser, every session after that came back `idle`. The console showed
"Recording · run 1 of 2" over a viewer that said the browser had ended.
"""

from __future__ import annotations

import json

import httpx
import pytest

from sro.application.ports.browser import BrowserUnavailable
from sro.domain.shared.identifiers import BrowserSessionId
from sro.infrastructure.steel import client as steel_module
from sro.infrastructure.steel.client import SteelClient

GHOST: dict[str, object] = {
    "id": "cc2b7d07-ghost",
    "status": "live",
    "createdAt": "2026-08-13T17:17:00.000Z",
}


@pytest.fixture(autouse=True)
def _no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """The poll is real; waiting for it in a unit test is not."""
    monkeypatch.setattr(steel_module, "_LIVE_POLL_SECONDS", 0)


def _steel(*, status: str, others: list[dict[str, object]] | None = None) -> SteelClient:
    released: list[str] = []
    # The list only holds a session once it has been created. Answering with it
    # beforehand made the fixture time-blind -- and the check that refuses to
    # take the browser from somebody else reads that list before it creates
    # anything.
    created: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/release"):
            released.append(path)
            return httpx.Response(200, json={"success": True})
        if request.method == "POST" and path == "/v1/sessions":
            created.append("new-session")
            return httpx.Response(
                201,
                json={
                    "id": "new-session",
                    "status": status,
                    "sessionViewerUrl": "http://0.0.0.0:3000/",
                    "debugUrl": "http://0.0.0.0:3000/v1/sessions/debug",
                },
            )
        if path == "/v1/sessions":
            mine = [{"id": "new-session", "status": status}] if created else []
            return httpx.Response(200, json={"sessions": [*(others or []), *mine]})
        if path.startswith("/v1/sessions/"):
            return httpx.Response(
                200,
                json={
                    "id": "new-session",
                    "status": status,
                    "sessionViewerUrl": "http://0.0.0.0:3000/",
                    "debugUrl": "http://0.0.0.0:3000/v1/sessions/debug",
                },
            )
        if path == "/json/version":
            return httpx.Response(200, json={"webSocketDebuggerUrl": "ws://localhost/devtools/x"})
        return httpx.Response(404)

    steel = SteelClient(
        "http://steel:3010",
        "http://steel:9223",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
    )
    steel.released = released
    return steel


async def test_a_session_with_a_browser_is_handed_back() -> None:
    session = await _steel(status="live").open()

    assert session.id == BrowserSessionId("new-session")
    assert session.debugger_url.startswith("ws://steel:9223/devtools/")


async def test_a_session_that_never_gets_a_browser_is_refused() -> None:
    """Steel answers 201 whether or not Chrome came up."""
    with pytest.raises(BrowserUnavailable, match="no browser attached"):
        await _steel(status="idle").open()


async def test_the_refusal_names_what_is_holding_the_only_browser() -> None:
    """The operator needs to know it is the ghost, not their request."""
    steel = _steel(status="idle", others=[GHOST])

    with pytest.raises(BrowserUnavailable) as refused:
        await steel.open()

    assert "cc2b7d07-ghost" in str(refused.value)
    assert "2026-08-13T17:17:00.000Z" in str(refused.value)
    assert "Restart the Steel container" in str(refused.value)


async def test_a_refused_session_is_not_left_behind() -> None:
    """Otherwise the failure adds another holder to the queue it complained about."""
    steel = _steel(status="idle")

    with pytest.raises(BrowserUnavailable):
        await steel.open()

    assert steel.released


async def test_a_release_that_changes_nothing_is_reported(caplog: pytest.LogCaptureFixture) -> None:
    """Steel answered 200 to releasing a dead session and left it live. Believing
    that 200 is what cost an afternoon."""
    steel = _steel(status="live")

    with caplog.at_level("WARNING"):
        await steel.close(BrowserSessionId("new-session"))

    assert "still reports it as live" in caplog.text


async def test_an_idle_session_has_no_live_view_to_show() -> None:
    """A viewer over a session with no browser renders an empty frame, which
    reads as "the operator's work vanished"."""
    assert await _steel(status="idle").live_view_url(BrowserSessionId("new-session")) is None
    assert await _steel(status="live").live_view_url(BrowserSessionId("new-session")) is not None


async def test_the_live_view_is_the_player_not_steel_s_own_console() -> None:
    """`sessionViewerUrl` is Steel's product UI: its header, Docs and Discord
    links, a details panel, and a Release Session button sitting inside our
    teaching screen — offering an operator a way to end the recording that we
    would never hear about."""
    steel = _steel(status="live")

    session = await steel.open()

    assert session.live_view_url.endswith("/v1/sessions/debug")


async def test_the_browser_is_never_taken_from_a_session_that_is_using_it() -> None:
    """Measured against the real thing: creating a session while another is
    `live` does not add a browser, it takes the one there is -- the previous
    session vanishes from the list mid-task. So a sign-in, a session check or a
    second pursuit silently killed whatever was on screen, and the thing that
    lost its browser reported that the screen had stopped responding to it."""
    steel = _steel(status="live", others=[{**GHOST, "id": "someone-working"}])

    with pytest.raises(BrowserUnavailable) as refused:
        await steel.open()

    assert "all are in use" in str(refused.value)
    assert "someone-working" in str(refused.value)
    assert steel.released == [], "nothing was created, so there is nothing to release"


async def test_a_session_is_created_without_steel_s_fingerprint_injector() -> None:
    """Steel's fingerprint injector attaches to every new tab and, when the tab
    is already gone, throws a `Target.attachToTarget` error nothing catches:
    Node exits and every account context in the container dies with it.
    Reproduced 3 of 3 by closing a tab right after opening it (S5 review C2)."""
    sent: list[dict[str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/sessions":
            sent.append(json.loads(request.content))
            return httpx.Response(201, json={"id": "s", "status": "live"})
        if request.url.path == "/json/version":
            return httpx.Response(200, json={"webSocketDebuggerUrl": "ws://localhost/devtools/x"})
        return httpx.Response(200, json={"sessions": []})

    steel = SteelClient(
        "http://steel:3010",
        "http://steel:9223",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
    )

    await steel.open()

    assert sent[0]["skipFingerprintInjection"] is True
