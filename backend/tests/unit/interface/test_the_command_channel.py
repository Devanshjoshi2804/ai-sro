"""The channel a browser holds open so work can be handed to it.

The correlation of commands and answers is proved against the registry in
``tests/unit/infrastructure``. What is proved here is the part a router owns:
who is allowed to open one at all, and that closing it leaves nothing behind
that a later run would try to drive.
"""

from __future__ import annotations

import time
import warnings
from collections.abc import Callable

import pytest

from sro.domain.observation.device import AgentDevice
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId
from sro.interface.http.app import create_app

with warnings.catch_warnings():
    # Same reason as test_watch: starlette asks for httpx2 at import, and a
    # websocket test is not a reason to add a second HTTP library.
    warnings.simplefilter("ignore")
    from starlette.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LAPTOP = DeviceId("dev-1")


@pytest.fixture
def wired() -> tuple[TestClient, _FakeContainer]:
    container = _FakeContainer(FakeUnitOfWork())
    app = create_app()
    # Deliberately not `with TestClient(app)`: the lifespan builds a real
    # container over this one, and these tests are about the router.
    app.state.container = container
    return TestClient(app), container


SECRET = "what-this-browser-was-minted-at-registration"  # noqa: S105 -- not a credential


def _register(container: _FakeContainer, *, tenant: TenantId = f.TENANT) -> None:
    at = f.at(0)
    container.unit_of_work().devices.rows[LAPTOP.value] = AgentDevice(
        id=LAPTOP,
        tenant_id=tenant,
        principal_id=f.OPERATOR,
        label="laptop",
        extension_version="0.1.0",
        registered_at=at,
        last_seen_at=at,
        secret=SECRET,
    )


def _eventually(check: Callable[[], bool], *, seconds: float = 1.0) -> bool:
    """The handler attaches just after the handshake returns to this side."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(0.01)
    return False


def test_a_connected_browser_is_reachable_and_a_closed_one_is_not(
    wired: tuple[TestClient, _FakeContainer],
) -> None:
    client, container = wired
    _register(container)

    with client.websocket_connect(
        f"/v1/agents/{LAPTOP}/commands", subprotocols=["bearer", token_for(), SECRET]
    ):
        assert _eventually(lambda: container.agent_sockets.online(f.TENANT) == (LAPTOP,))

    # Nothing left behind: a run that reached for this device now finds no
    # browser rather than a socket nobody is listening to.
    assert _eventually(lambda: container.agent_sockets.online(f.TENANT) == ())


def test_a_browser_that_went_does_not_become_an_unhandled_exception(
    wired: tuple[TestClient, _FakeContainer],
) -> None:
    """Closing a socket that has already gone is not a failure, and there is
    nothing left to do about it either way.

    `RuntimeError` alone was not enough. A browser that goes -- an extension
    reloaded, a laptop shut, a tunnel dropped -- leaves the `close()` in the
    endpoint's `finally` writing a close frame to nobody, and uvicorn answers
    that with `ClientDisconnected`, which is neither a `RuntimeError` nor
    importable from here without reaching into a server's internals. It went
    uncaught, out of the endpoint, and printed thirty lines of `Exception in
    ASGI application` for the ordinary event that `finally` exists to handle.
    Measured on the deployment 2026-09-21: two of them against three
    reconnections.

    Raised from the CLOSE, which is the frame the traceback named, and with a
    type that is not a `RuntimeError` -- the two facts that made this escape.
    """
    from starlette.websockets import WebSocket

    client, container = wired
    _register(container)

    # What uvicorn does when the peer has gone: a type that is NOT a
    # `RuntimeError`, raised from the close itself.
    async def gone(self: WebSocket, *args: object, **kwargs: object) -> None:
        raise ConnectionResetError("the browser went")

    was = WebSocket.close
    WebSocket.close = gone  # type: ignore[method-assign, assignment]
    try:
        with client.websocket_connect(
            f"/v1/agents/{LAPTOP}/commands", subprotocols=["bearer", token_for(), SECRET]
        ):
            assert _eventually(lambda: container.agent_sockets.online(f.TENANT) == (LAPTOP,))
        # Detached, said, and nothing thrown past the endpoint.
        assert _eventually(lambda: container.agent_sockets.online(f.TENANT) == ())
    finally:
        WebSocket.close = was  # type: ignore[method-assign]


def test_a_socket_without_a_credential_is_closed_rather_than_served(
    wired: tuple[TestClient, _FakeContainer],
) -> None:
    """The same browser connects with its credential afterwards, and is served.

    A websocket path nobody registered is closed too, and leaves the same empty
    register behind, so a refusal on its own proves this channel guarded and
    absent at the same time -- the 404 problem the HTTP doors have, in the one
    shape that has no status code to read.
    """
    client, container = wired
    _register(container)

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"/v1/agents/{LAPTOP}/commands"),
    ):
        pass

    assert container.agent_sockets.online(f.TENANT) == ()

    with client.websocket_connect(
        f"/v1/agents/{LAPTOP}/commands", subprotocols=["bearer", token_for(), SECRET]
    ):
        assert _eventually(lambda: container.agent_sockets.online(f.TENANT) == (LAPTOP,))


def test_another_tenants_device_is_closed_exactly_like_one_that_is_not_there(
    wired: tuple[TestClient, _FakeContainer],
) -> None:
    """A valid credential proves who is asking, never what they may address. A
    device id that leaked is otherwise a browser somebody else can hand work to.

    The same id is re-registered to the caller's own tenant and connects, which
    is what makes the refusal about the tenant: an unregistered websocket path
    is closed just the same and leaves both registers just as empty.
    """
    client, container = wired
    _register(container, tenant=TenantId("other-corp"))

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            f"/v1/agents/{LAPTOP}/commands", subprotocols=["bearer", token_for(), SECRET]
        ),
    ):
        pass

    assert container.agent_sockets.online(f.TENANT) == ()
    assert container.agent_sockets.online(TenantId("other-corp")) == ()

    _register(container)
    with client.websocket_connect(
        f"/v1/agents/{LAPTOP}/commands", subprotocols=["bearer", token_for(), SECRET]
    ):
        assert _eventually(lambda: container.agent_sockets.online(f.TENANT) == (LAPTOP,))


def test_a_device_nobody_registered_cannot_open_a_channel(
    wired: tuple[TestClient, _FakeContainer],
) -> None:
    """Registering the row is the whole of the difference, and it is made in
    this test rather than assumed: the same subprotocols are refused before it
    and served after. Without the second half, a channel route that had been
    deleted outright would pass -- an unmatched websocket path is closed too.
    """
    client, container = wired

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            f"/v1/agents/{LAPTOP}/commands", subprotocols=["bearer", token_for(), SECRET]
        ),
    ):
        pass

    assert container.agent_sockets.online(f.TENANT) == ()

    _register(container)
    with client.websocket_connect(
        f"/v1/agents/{LAPTOP}/commands", subprotocols=["bearer", token_for(), SECRET]
    ):
        assert _eventually(lambda: container.agent_sockets.online(f.TENANT) == (LAPTOP,))


def test_a_credential_for_another_principal_of_the_same_tenant_may_connect(
    wired: tuple[TestClient, _FakeContainer],
) -> None:
    """Deliberate, and worth stating: authorisation here is per tenant and per
    device, never per principal -- a per-principal boundary would need a role
    model, and inventing half of one here would read as more than it is. What
    stops a colleague reaching this browser is not who they are, it is that
    they do not hold what it was minted at registration.
    """
    client, container = wired
    _register(container)
    other = PrincipalId("someone.else@acme.test")

    with client.websocket_connect(
        f"/v1/agents/{LAPTOP}/commands",
        subprotocols=["bearer", token_for(principal=other.value), SECRET],
    ):
        assert _eventually(lambda: container.agent_sockets.online(f.TENANT) == (LAPTOP,))


def test_a_browser_that_cannot_prove_it_is_itself_is_closed_like_one_that_is_not_there(
    wired: tuple[TestClient, _FakeContainer],
) -> None:
    """A valid tenant credential is not this browser.

    It is the whole of the gap this secret closes: every device-scoped path is
    `/v1/agents/{device_id}/...`, so without it a colleague's extension -- a
    perfectly good credential, the wrong browser -- is any device it can name,
    and this socket is how work is handed to one.

    Refused identically whether nothing was presented, something wrong was, or
    the device never existed. A close code that differed would let a caller
    holding no secret at all learn which ids are real.

    And the secret it really was minted with opens it, in the same test: three
    identical closes are also what three attempts at a path nobody registered
    look like, so the secret has to be shown to be the thing being read.
    """
    client, container = wired
    _register(container)

    for presented in ([], ["bearer", token_for()], ["bearer", token_for(), "not-the-secret"]):
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect(f"/v1/agents/{LAPTOP}/commands", subprotocols=presented),
        ):
            pass

    assert container.agent_sockets.online(f.TENANT) == ()

    with client.websocket_connect(
        f"/v1/agents/{LAPTOP}/commands", subprotocols=["bearer", token_for(), SECRET]
    ):
        assert _eventually(lambda: container.agent_sockets.online(f.TENANT) == (LAPTOP,))
