"""The tenant's three doors onto its browsers: the roster, the revoke, the restore.

Ported from `new_agent_arch/src/rig/api.py:988-1019`, over the whole stack down
to the in-memory store, because what breaks here is wiring rather than rules:
the use cases have their own tests in
`tests/unit/application/rig/test_devices.py`, and none of them can see a router
pointed at the wrong container factory, a `moved` read off the wrong boolean, or
a device secret let through a door that is the tenant's alone.

`restore` has no rig ancestor. The rig's `issue` un-revoked as a side effect of
minting a fresh token; registration here is idempotent and hands back the same
secret, so until this route existed the only way back from a wrong press was a
hand-edited row.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from sro.domain.observation.device import AgentDevice
from sro.domain.shared.identifiers import DeviceId
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LAPTOP = DeviceId("dev-1")
DESKTOP = DeviceId("dev-2")
HERS = "the-secret-this-browser-was-minted"


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    return _FakeContainer(uow)


@pytest.fixture
async def client(container: _FakeContainer) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for()}"},
    ) as http:
        yield http


@pytest.fixture
async def registered(uow: FakeUnitOfWork) -> AgentDevice:
    """One browser, with a secret it can really prove itself with.

    Dated `f.at(...)` rather than "now": a fixture stamped with the wall clock
    passes on the day it is written and drifts under every assertion about
    order or age afterwards.
    """
    device = f.device(id=LAPTOP, secret=HERS, registered_at=f.at(0), last_seen_at=f.at(60))
    await uow.devices.add(device)
    return device


async def test_a_browser_is_revoked_and_the_second_press_moves_nothing(
    client: httpx.AsyncClient, registered: AgentDevice
) -> None:
    first = await client.post(f"/v1/devices/{LAPTOP.value}/revoke")
    second = await client.post(f"/v1/devices/{LAPTOP.value}/revoke")

    assert first.status_code == 200
    assert first.json() == {"device_id": LAPTOP.value, "moved": True}
    # The first revocation's instant is what an audit is read against, so the
    # second press answers `moved: False` rather than moving it.
    assert second.json() == {"device_id": LAPTOP.value, "moved": False}


async def test_revoking_a_browser_this_tenant_does_not_have_is_a_404(
    client: httpx.AsyncClient, registered: AgentDevice
) -> None:
    """A different answer from `moved: False`, and deliberately.

    "No such browser" and "nothing live to revoke" are not the same fact, and a
    route that swallowed the first into the second would let a tenant press at
    another tenant's device ids and learn nothing -- but would also tell an
    administrator who mistyped an id that the press had worked.
    """
    answered = await client.post("/v1/devices/nobody/revoke")

    assert answered.status_code == 404
    assert answered.json()["detail"] == "device nobody was not found"


async def test_restoring_a_browser_this_tenant_does_not_have_is_a_404(
    client: httpx.AsyncClient, registered: AgentDevice
) -> None:
    """The revoke's two answers again, at the other door: "no such browser" is
    not "nothing to restore".

    The registered browser is pressed in the same test on purpose: a 404 alone
    passes against a path nobody registered -- Starlette's own miss goes
    through `_http_problem` and answers the same `not_found` problem document
    -- so the route would be proved tenant-scoped and absent at once.
    """
    assert (await client.post("/v1/devices/nobody/restore")).status_code == 404

    mine = await client.post(f"/v1/devices/{LAPTOP.value}/restore")

    assert mine.status_code == 200
    assert mine.json() == {"device_id": LAPTOP.value, "moved": False}


async def test_a_browser_may_not_revoke_or_restore_or_read_the_roster(
    client: httpx.AsyncClient, registered: AgentDevice
) -> None:
    """Tenant-only: the money and the other browsers are not a browser's to
    touch. A device secret on these paths is not a second way in.

    Named with its own id and its own real secret, which is the only way to
    reach `tenant_only` at all -- a wrong or half-offered secret is refused
    earlier, by `asking_device`, as a 404.
    """
    proving = {"X-Device-Secret": HERS}
    at = f"?device_id={LAPTOP.value}"

    refusals = [
        await client.post(f"/v1/devices/{LAPTOP.value}/revoke{at}", headers=proving),
        await client.post(f"/v1/devices/{LAPTOP.value}/restore{at}", headers=proving),
        await client.get(f"/v1/devices{at}", headers=proving),
    ]

    assert [answered.status_code for answered in refusals] == [403, 403, 403]
    assert refusals[0].json()["detail"] == "that is the tenant's to do, not a browser's"
    # And nothing moved: a 403 that had already written the row would be the
    # worst of both.
    assert (await client.get("/v1/devices")).json()["devices"][0]["revoked_at"] is None


async def test_the_roster_says_which_browsers_are_connected(
    client: httpx.AsyncClient, registered: AgentDevice
) -> None:
    body = (await client.get("/v1/devices")).json()

    assert [line["online"] for line in body["devices"]] == [False]
    assert body["devices"][0]["device_id"] == LAPTOP.value
    assert body["devices"][0]["label"] == registered.label


async def test_a_revoked_browser_stays_on_the_roster_carrying_when_it_ended(
    client: httpx.AsyncClient, registered: AgentDevice
) -> None:
    # The list is read before cutting a browser off and after. A revocation
    # that erased its own subject would leave an administrator unable to
    # confirm the thing they just did.
    await client.post(f"/v1/devices/{LAPTOP.value}/revoke")

    (line,) = (await client.get("/v1/devices")).json()["devices"]

    assert line["device_id"] == LAPTOP.value
    assert line["revoked_at"] is not None
    assert line["online"] is False


async def test_a_restored_browser_is_on_the_roster_with_no_revocation(
    client: httpx.AsyncClient, registered: AgentDevice
) -> None:
    await client.post(f"/v1/devices/{LAPTOP.value}/revoke")

    restored = await client.post(f"/v1/devices/{LAPTOP.value}/restore")

    assert restored.json() == {"device_id": LAPTOP.value, "moved": True}
    (line,) = (await client.get("/v1/devices")).json()["devices"]
    assert line["revoked_at"] is None
    # And a browser that was never revoked: the press is idempotent, and an
    # administrator pressing twice has not made a mistake worth an error page.
    assert (await client.post(f"/v1/devices/{LAPTOP.value}/restore")).json()["moved"] is False


async def test_the_press_names_the_browser_in_the_path(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, registered: AgentDevice
) -> None:
    """The sibling browser is what goes wrong at a router: an administrator
    cutting off the desktop and finding the laptop dark. The path segment has
    to reach the use case, and only two browsers can show that it did."""
    await uow.devices.add(f.device(id=DESKTOP, label="desktop", last_seen_at=f.at(30)))

    await client.post(f"/v1/devices/{DESKTOP.value}/revoke")

    ended = {
        line["device_id"]: line["revoked_at"]
        for line in (await client.get("/v1/devices")).json()["devices"]
    }
    assert ended[LAPTOP.value] is None
    assert ended[DESKTOP.value] is not None


async def test_the_roster_is_most_recently_seen_first(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, registered: AgentDevice
) -> None:
    """Inherited from `list_for_tenant` rather than chosen, and the order the
    question wants: an administrator asking who can act cares which browser was
    here this morning, not which was installed first.

    The desktop is added second and seen later, so the answer is the REVERSE of
    the order the store was written in. A router that passed the rows through
    in whatever order it got them would otherwise agree with this by accident.
    """
    await uow.devices.add(f.device(id=DESKTOP, label="desktop", last_seen_at=f.at(120)))

    body = (await client.get("/v1/devices")).json()

    assert [line["device_id"] for line in body["devices"]] == [DESKTOP.value, LAPTOP.value]


async def test_the_older_agents_listing_learned_the_same_online_answer(
    client: httpx.AsyncClient, registered: AgentDevice
) -> None:
    """`GET /v1/agents` now runs through `ReadRoster` too.

    It was the one caller of a second use case over the identical
    `list_for_tenant`, which is how two lists of the same thing start
    disagreeing. `online` is what it gained by the move.
    """
    (device,) = (await client.get("/v1/agents")).json()

    assert device["id"] == LAPTOP.value
    assert device["online"] is False


class _Attached:
    """A browser holding a command channel. Nothing is ever sent down it; what
    the roster reads is that the registry has one at all."""

    async def send_text(self, text: str) -> None:  # pragma: no cover - never called
        raise AssertionError("the roster must not talk to a browser")


async def test_the_roster_reports_a_browser_that_actually_holds_a_channel(
    client: httpx.AsyncClient, container: _FakeContainer, registered: AgentDevice
) -> None:
    """Every other roster assertion in this suite reads `online is False`,
    because nothing had ever attached a socket -- so hardcoding the field to
    `False` passed the whole suite. `online` is the question this list is read
    to answer, and this is the only test that watches it say yes.

    Attached to the container's own `agent_sockets`, which is what
    `container.agents()` builds its drivers over: a test that overrode the
    drivers instead would prove the model and not the wiring.
    """
    container.agent_sockets.attach(f.TENANT, LAPTOP, _Attached())

    (line,) = (await client.get("/v1/devices")).json()["devices"]

    assert line["online"] is True
    # And `GET /v1/agents`, which runs through the same `ReadRoster`.
    assert (await client.get("/v1/agents")).json()[0]["online"] is True


async def test_a_revoked_browser_reads_offline_even_holding_a_channel(
    client: httpx.AsyncClient, container: _FakeContainer, registered: AgentDevice
) -> None:
    """The row is the authority; the socket is a fact about a wire.

    `RevokeDevice` drops the channel, so normally there is nothing to report --
    this attaches one back afterwards, which is what a browser that reconnected
    after its revocation does. Reading it as connected on the list an
    administrator answers "who can act" from is the whole of what that drop was
    for.
    """
    await client.post(f"/v1/devices/{LAPTOP.value}/revoke")
    container.agent_sockets.attach(f.TENANT, LAPTOP, _Attached())

    (line,) = (await client.get("/v1/devices")).json()["devices"]

    assert line["revoked_at"] is not None
    assert line["online"] is False
