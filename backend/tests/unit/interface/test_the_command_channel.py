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


def _register(container: _FakeContainer, *, tenant: TenantId = f.TENANT) -> None:
    at = f.at(0)
    container.unit_of_work().devices.rows[LAPTOP.value] = AgentDevice(  # type: ignore[attr-defined]
        id=LAPTOP,
        tenant_id=tenant,
        principal_id=f.OPERATOR,
        label="laptop",
        extension_version="0.1.0",
        registered_at=at,
        last_seen_at=at,
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
        f"/v1/agents/{LAPTOP}/commands", subprotocols=["bearer", token_for()]
    ):
        assert _eventually(lambda: container.agent_sockets.online(f.TENANT) == (LAPTOP,))

    # Nothing left behind: a run that reached for this device now finds no
    # browser rather than a socket nobody is listening to.
    assert _eventually(lambda: container.agent_sockets.online(f.TENANT) == ())


def test_a_socket_without_a_credential_is_closed_rather_than_served(
    wired: tuple[TestClient, _FakeContainer],
) -> None:
    client, container = wired
    _register(container)

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"/v1/agents/{LAPTOP}/commands"),
    ):
        pass

    assert container.agent_sockets.online(f.TENANT) == ()


def test_another_tenants_device_is_closed_exactly_like_one_that_is_not_there(
    wired: tuple[TestClient, _FakeContainer],
) -> None:
    """A valid credential proves who is asking, never what they may address. A
    device id that leaked is otherwise a browser somebody else can hand work to.
    """
    client, container = wired
    _register(container, tenant=TenantId("other-corp"))

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            f"/v1/agents/{LAPTOP}/commands", subprotocols=["bearer", token_for()]
        ),
    ):
        pass

    assert container.agent_sockets.online(f.TENANT) == ()
    assert container.agent_sockets.online(TenantId("other-corp")) == ()


def test_a_device_nobody_registered_cannot_open_a_channel(
    wired: tuple[TestClient, _FakeContainer],
) -> None:
    client, container = wired

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            f"/v1/agents/{LAPTOP}/commands", subprotocols=["bearer", token_for()]
        ),
    ):
        pass

    assert container.agent_sockets.online(f.TENANT) == ()


def test_a_credential_for_another_principal_of_the_same_tenant_may_connect(
    wired: tuple[TestClient, _FakeContainer],
) -> None:
    """Deliberate, and worth stating: authorisation here is per tenant, because
    that is the only boundary this system has. A per-principal one would need a
    role model, and inventing half of one here would read as more than it is.
    """
    client, container = wired
    _register(container)
    other = PrincipalId("someone.else@acme.test")

    with client.websocket_connect(
        f"/v1/agents/{LAPTOP}/commands",
        subprotocols=["bearer", token_for(principal=other.value)],
    ):
        assert _eventually(lambda: container.agent_sockets.online(f.TENANT) == (LAPTOP,))
