"""Watching a browser session over a websocket.

The provider's own viewer is one page for the whole deployment -- no session in
the URL -- so an operator pressing "Watch it" got a browser that was not theirs,
or "Session connecting..." for a browser that had been released an hour ago.
"""

from __future__ import annotations

import warnings

import pytest

from sro.application.context import RequestContext
from sro.interface.http.app import create_app

with warnings.catch_warnings():
    # Starlette wants `httpx2` for its test client and warns at import; the
    # project pins httpx, and a websocket test is not a reason to add a second
    # HTTP library to the dependency tree.
    warnings.simplefilter("ignore")
    from starlette.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for


@pytest.fixture
def app_and_container() -> tuple[TestClient, _FakeContainer]:
    container = _FakeContainer(FakeUnitOfWork())
    app = create_app()
    app.state.container = container
    return TestClient(app), container


async def test_the_frames_are_of_the_session_that_was_asked_for(
    app_and_container: tuple[TestClient, _FakeContainer],
) -> None:
    client, container = app_and_container
    mine = await container.browsers().open(
        RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
    )

    with client.websocket_connect(
        f"/v1/browser/{mine.id}/live", subprotocols=["bearer", token_for()]
    ) as socket:
        assert socket.receive_bytes() == container.browser.screen[0]
        assert socket.receive_bytes() == container.browser.screen[1]


def test_a_socket_without_a_credential_is_closed_rather_than_served(
    app_and_container: tuple[TestClient, _FakeContainer],
) -> None:
    """A websocket cannot carry an Authorization header, which is not the same
    as not needing one: unchecked, this streams any operator's screen to
    anybody who can guess a session id."""
    client, _ = app_and_container

    with (
        pytest.raises(WebSocketDisconnect) as refused,
        client.websocket_connect("/v1/browser/sess-1/live") as socket,
    ):
        socket.receive_bytes()

    assert refused.value.code == 1008


async def test_another_tenant_is_refused_the_browser_it_did_not_open(
    app_and_container: tuple[TestClient, _FakeContainer],
) -> None:
    """Session ids are handed out by `/v1/connections/browsers`, so a token and
    one listing was the whole cost of watching somebody else's warehouse."""
    client, container = app_and_container
    mine = await container.browsers().open(
        RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
    )

    with (
        pytest.raises(WebSocketDisconnect) as refused,
        client.websocket_connect(
            f"/v1/browser/{mine.id}/live", subprotocols=["bearer", token_for(tenant="rival")]
        ) as socket,
    ):
        socket.receive_bytes()

    assert refused.value.code == 1008
