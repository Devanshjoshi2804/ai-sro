"""Every `/v1/agents/{device_id}/...` path, and the one thing they all ask.

The credential these routes have always taken is the tenant's. It says which
tenant is asking and it cannot say which browser, so the device id in the path
was a namespace rather than a credential: any extension holding a valid tenant
token was every device it could name. That was uncomfortable while these routes
listed watches and held a socket. `.../fire` starts a run in a live warehouse.

So a device now carries a secret, minted at registration, presented on every
device-scoped call -- the shape a trigger's `inbound_token` already has for a
caller with no principal behind it, and the same rule about what a wrong one
may reveal.

Four rules, asserted here over every route together rather than one at a time,
because a gap left on one of them is the whole gap.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from sro.domain.observation.device import AgentDevice
from sro.domain.shared.identifiers import DeviceId, PrincipalId
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LENA = DeviceId("dev-lena-laptop")
SAM = DeviceId("dev-sam-laptop")

HERS = "the-secret-lena-s-browser-was-minted"
HIS = "the-secret-sam-s-browser-was-minted"


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


def _device(uow: FakeUnitOfWork, device_id: DeviceId, secret: str | None) -> None:
    uow.devices.rows[device_id.value] = AgentDevice(
        id=device_id,
        tenant_id=f.TENANT,
        principal_id=PrincipalId(f"{device_id.value}@acme.test"),
        label=device_id.value,
        extension_version="0.1.0",
        registered_at=f.at(0),
        last_seen_at=f.at(0),
        secret=secret,
    )


async def _every_route(
    client: httpx.AsyncClient, device_id: DeviceId, *, secret: str | None
) -> list[httpx.Response]:
    """Everything under `/v1/agents/{device_id}/`.

    Listed here rather than parametrised so that a route added later and not
    added here is visible as an absence in one place.
    """
    headers = {} if secret is None else {"X-Device-Secret": secret}
    at = f"/v1/agents/{device_id.value}"
    return [
        await client.post(f"{at}/heartbeat", json={}, headers=headers),
        await client.get(f"{at}/watches", headers=headers),
        await client.post(f"{at}/watches/trg-1/matched", json={}, headers=headers),
        await client.post(f"{at}/watches/trg-1/fire", json={}, headers=headers),
    ]


def _readable(response: httpx.Response) -> tuple[int, object]:
    """Everything a caller can read a difference out of.

    `instance` is the path that was asked for, so it differs by construction
    and says nothing the caller did not already write.
    """
    body = dict(response.json())
    body.pop("instance", None)
    return response.status_code, body


async def test_a_browser_presenting_no_secret_is_refused_everywhere(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Including the absent header, which must not be a 422 that names it.

    A validation error saying `X-Device-Secret` is required is an answer: it
    confirms the route, and a caller working out what to try next is exactly
    who must learn nothing here.

    Lena's real secret is offered at the end, over the same four paths: 404
    everywhere is also what four routes nobody registered answer, in the same
    words and the same problem document, so without a call that must be served
    these doors would be proved shut and absent at the same time.
    """
    _device(uow, LENA, HERS)

    for response in await _every_route(client, LENA, secret=None):
        assert response.status_code == 404, response.text
    for response in await _every_route(client, LENA, secret=""):
        assert response.status_code == 404, response.text

    beat, watches, _, _ = await _every_route(client, LENA, secret=HERS)
    assert (beat.status_code, watches.status_code) == (200, 200), beat.text


async def test_another_browsers_secret_reads_exactly_like_a_device_that_never_existed(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Sam's extension, holding Sam's secret, asking about Lena's browser.

    The credential is valid and the tenant is right -- that is the whole shape
    of the problem. What comes back has to be indistinguishable from asking
    about a device id nobody ever registered, or the difference is a way to
    enumerate which of a tenant's browsers are real.

    Asked about the same id both times, so the comparison is on the answer and
    not on the sentence quoting back what the caller wrote.

    Sam asks about Sam's own browser first, and is served. Two lists of 404s
    are equal to each other whether the secret is being checked or the four
    routes were never registered at all -- an unmatched path answers the same
    `not_found` document through the same handler -- so the indistinguishable
    pair means nothing until something here is distinguishable.
    """
    _device(uow, LENA, HERS)
    _device(uow, SAM, HIS)

    beat, watches, _, _ = await _every_route(client, SAM, secret=HIS)
    assert (beat.status_code, watches.status_code) == (200, 200), beat.text

    stolen = await _every_route(client, LENA, secret=HIS)
    uow.devices.rows.pop(LENA.value)
    never_existed = await _every_route(client, LENA, secret=HIS)

    assert [_readable(response) for response in stolen] == [
        _readable(response) for response in never_existed
    ]
    assert all(response.status_code == 404 for response in stolen)


async def test_a_browser_presenting_its_own_secret_is_served(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The heartbeat and the rules answer; the two watch paths get as far as
    looking for a watch and find none, which is a different 404 from the one
    above -- it is the trigger that is missing, not the browser."""
    _device(uow, LENA, HERS)

    beat, watches, matched, fired = await _every_route(client, LENA, secret=HERS)

    assert beat.status_code == 200, beat.text
    assert watches.status_code == 200, watches.text
    assert watches.json() == []
    assert matched.json()["detail"] == "no such watch"
    assert fired.json()["detail"] == "no such watch"


async def test_a_device_from_before_secrets_existed_is_refused_and_not_stranded(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The migration, in one test.

    A row registered before this column existed holds no secret, so it proves
    nothing and is refused like any stranger -- backfilling one would be a
    secret nobody could tell the browser about. What the browser does about it
    is register again: idempotent on (tenant, principal, label), so it comes
    back as the same device, same id, now holding a secret it can present. One
    heartbeat's worth of "still here" is the whole of what the operator sees.
    """
    _device(uow, LENA, None)
    stale = uow.devices.rows[LENA.value]

    for response in await _every_route(client, LENA, secret=""):
        assert response.status_code == 404, response.text

    again = await client.post(
        "/v1/agents/register",
        json={"label": stale.label, "extension_version": "0.1.0"},
        headers={"Authorization": f"Bearer {token_for(principal=stale.principal_id.value)}"},
    )

    assert again.status_code == 201, again.text
    assert again.json()["device_id"] == LENA.value
    minted = again.json()["device_secret"]
    assert minted
    for response in await _every_route(client, LENA, secret=minted):
        assert response.status_code != 404 or response.json()["detail"] == "no such watch"
