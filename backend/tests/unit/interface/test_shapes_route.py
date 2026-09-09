"""The list the extension matches a live tail against.

Ported from `new_agent_arch/src/rig/api.py:1533-1546`. No model is on this
path: arithmetic out and arithmetic in, which is why it can be asked on every
page an operator opens. What is worth holding here is who the rest belongs to
-- a job a browser refused three times comes back quiet for that browser and
for nobody else, so the identity this route passes down is the whole of its
behaviour.

Over the whole stack down to the in-memory store, and through the `client`
fixture rather than by calling the dependency: these are the first tests in the
suite that send `?device_id=` and `X-Device-Secret` as real request inputs.
`asking_device` declares them `Query()` and `Header()`, `test_which_browser_is_asking`
calls it positionally, and until this file existed changing `Query()` to
`Header()` -- which breaks `?device_id=` outright, the exact parameter that
module's security claim is about -- left the whole suite green.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import timedelta

import httpx
import pytest
from httpx import ASGITransport

from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import DeviceId
from sro.domain.skill.offers import Offer
from sro.domain.skill.workflow import Step, Workflow
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LAPTOP = DeviceId("dev-1")
DESKTOP = DeviceId("dev-2")
HERS = "the-secret-the-laptop-was-minted"
THEIRS = "the-secret-the-desktop-was-minted"
HOST = "http://127.0.0.1:63319"
JOB = "wfl_1"


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


def _typed(by_id: dict[str, Gesture]) -> Gesture:
    return next(
        g for g in by_id.values() if g.action.kind == "type" and g.action.value == "ACME-4471"
    )


def _saver(by_id: dict[str, Gesture]) -> Gesture:
    """The click on Save, by its control and not by position."""
    return next(
        g
        for g in by_id.values()
        if g.action.target
        and g.action.target.component
        and g.action.target.component.item_id == "saveButton"
    )


@pytest.fixture
def evidence() -> dict[str, Gesture]:
    """The one measured batch every other rig test is built on.

    A fixture and not a call per test: `correlate` mints a fresh random id for
    every gesture, so a second call produces evidence the store does not hold
    and a workflow citing it is served as nothing.
    """
    return {g.id: g for g in _gestures(f.TENANT.value)}


@pytest.fixture
async def proven(uow: FakeUnitOfWork, evidence: dict[str, Gesture]) -> Workflow:
    """One workflow the extension can be served, and two browsers to serve it to.

    Built on the measured batch, so what this file asserts about a shape is the
    shape the arithmetic really produces.
    """
    by_id = evidence
    await uow.gestures.add_gestures(tuple(by_id.values()))
    workflow = Workflow(
        id=JOB,
        tenant=f.TENANT.value,
        title="create a client",
        narrative="n",
        systems=[HOST],
        steps=[
            Step(
                order=0,
                says="type the code",
                system=None,
                cites=[_typed(by_id).id],
                parameters=["clientCode"],
            ),
            Step(order=1, says="save", system=None, cites=[_saver(by_id).id]),
        ],
        parameters=[{"name": "clientCode", "seen_values": ["ACME-4471"]}],
    )
    await uow.workflows.save(workflow)
    await uow.devices.add(f.device(id=LAPTOP, secret=HERS))
    await uow.devices.add(f.device(id=DESKTOP, label="desktop", secret=THEIRS))
    return workflow


async def _refused(uow: FakeUnitOfWork, container: _FakeContainer, device: DeviceId) -> None:
    """Three offers of this job turned down in a row, by one browser.

    Dated off the container's clock, which is six months from the wall
    calendar: a rest is the last refusal plus a day, so a route reading
    `datetime.now(UTC)` instead of the clock it was built with finds these
    offers long expired and answers `quiet_until: null` to everybody.
    """
    at = container.clock.now() - timedelta(hours=1)
    for i in range(3):
        await uow.offers.record(
            Offer(
                id=f"off_{device.value}_{i}",
                tenant=f.TENANT.value,
                workflow_id=JOB,
                device_id=device.value,
                k=2,
                fate="dismissed",
                at=(at + timedelta(minutes=i)).isoformat(),
            )
        )


async def _asking_as(client: httpx.AsyncClient, device: DeviceId, secret: str) -> httpx.Response:
    """One request carrying the two halves a browser proves itself with, where
    a real one carries them: the id in the query string, the secret in a
    header. Nothing else in the suite sends either as a request input."""
    return await client.get(
        "/v1/shapes",
        params={"device_id": device.value},
        headers={"X-Device-Secret": secret},
    )


# --- the wire shape -------------------------------------------------------


async def test_the_list_comes_back_under_the_shapes_key(
    client: httpx.AsyncClient, proven: Workflow
) -> None:
    """An object and not a bare list, which is what the rig answered and what
    `recognise.js` reads. A route returning the list itself would type-check,
    serialise and 200 -- and the extension would find no `shapes` key."""
    answered = await client.get("/v1/shapes")

    assert answered.status_code == 200
    body = answered.json()
    assert isinstance(body, dict)
    assert [shape["id"] for shape in body["shapes"]] == [JOB]
    # The arithmetic really ran: this is not an empty envelope agreeing with a
    # key check by accident.
    assert body["shapes"][0]["title"] == "create a client"
    assert body["shapes"][0]["starts_on"] == f"{HOST}/"
    assert HOST in body["shapes"][0]["hosts"]
    assert body["shapes"][0]["parameters"] == [{"name": "clientCode", "at": 0}]


async def test_every_proven_job_comes_back_and_in_the_order_it_was_served(
    client: httpx.AsyncClient,
    uow: FakeUnitOfWork,
    evidence: dict[str, Gesture],
    proven: Workflow,
) -> None:
    """The route passes the list through: it does not re-order it and it does
    not trim it.

    Two jobs, because one agrees with a route that reversed, sliced or dropped
    the list. `known()` is oldest first, so the answer is insertion order --
    and the second job is saved with the LOWER id, so a route that sorted (or a
    store that handed back a tie in id order) is not satisfied by this plant
    either.
    """
    await uow.workflows.save(
        Workflow(
            id="wfl_0",
            tenant=f.TENANT.value,
            title="save it",
            narrative="n",
            systems=[HOST],
            steps=[Step(order=0, says="save", system=None, cites=[_saver(evidence).id])],
        )
    )

    body = (await client.get("/v1/shapes")).json()

    assert [shape["id"] for shape in body["shapes"]] == [JOB, "wfl_0"]


async def test_a_tenant_with_nothing_proven_is_answered_with_an_empty_list(
    client: httpx.AsyncClient,
) -> None:
    assert (await client.get("/v1/shapes")).json() == {"shapes": []}


async def test_no_credential_is_refused_before_anything_is_read(
    client: httpx.AsyncClient, proven: Workflow
) -> None:
    answered = await client.get("/v1/shapes", headers={"Authorization": ""})

    assert answered.status_code == 401


# --- whose rest it is -----------------------------------------------------


async def test_the_rest_a_browser_earned_is_served_to_that_browser(
    client: httpx.AsyncClient,
    uow: FakeUnitOfWork,
    container: _FakeContainer,
    proven: Workflow,
) -> None:
    """The whole of this route's behaviour, and the argument that must not be
    dropped on the way to the use case.

    The laptop refused this job three times running; the desktop has never been
    offered it. Two browsers, because a route that passed `None` down -- or
    passed the tenant's own id, or a literal -- would agree with a one-browser
    test either way.
    """
    await _refused(uow, container, LAPTOP)

    laptop = await _asking_as(client, LAPTOP, HERS)
    desktop = await _asking_as(client, DESKTOP, THEIRS)

    assert laptop.json()["shapes"][0]["quiet_until"] is not None
    assert desktop.json()["shapes"][0]["quiet_until"] is None
    # And the job is still served to the browser resting it: the list stays
    # whole and cacheable, and `recognise.js` is what declines to offer it.
    assert [shape["id"] for shape in laptop.json()["shapes"]] == [JOB]


async def test_the_tenant_asking_without_naming_a_browser_rests_nothing(
    client: httpx.AsyncClient,
    uow: FakeUnitOfWork,
    container: _FakeContainer,
    proven: Workflow,
) -> None:
    """With no browser named there is nobody to rest. A route that fell back to
    some browser's id when none was proved would hand one operator's no to
    every other operator in the tenant."""
    await _refused(uow, container, LAPTOP)

    answered = await client.get("/v1/shapes")

    assert answered.json()["shapes"][0]["quiet_until"] is None


async def test_a_browser_cannot_read_another_browsers_rest(
    client: httpx.AsyncClient,
    uow: FakeUnitOfWork,
    container: _FakeContainer,
    proven: Workflow,
) -> None:
    """The rig's rule, kept: the secret names the browser, the query does not.

    The secret is the laptop's and the query says the desktop, and the answer
    is a 404 rather than the desktop's list. `asking_device` refuses a mismatch
    rather than resolving it, and this route inherits that by not looking.
    """
    await _refused(uow, container, DESKTOP)

    answered = await client.get(
        "/v1/shapes",
        params={"device_id": DESKTOP.value},
        headers={"X-Device-Secret": HERS},
    )

    assert answered.status_code == 404
    assert answered.json()["detail"] == f"device {DESKTOP.value} was not found"


async def test_a_query_string_alone_does_not_name_a_browser(
    client: httpx.AsyncClient,
    uow: FakeUnitOfWork,
    container: _FakeContainer,
    proven: Workflow,
) -> None:
    """Without this, `?device_id=` is an impersonation parameter: every
    device-scoped answer would be one query string away from any credential in
    the tenant. A refusal and never a quiet downgrade to the tenant.

    The tenant's own read is taken in the same test, and it is what "never a
    quiet downgrade" is measured against: the same door, the same credential,
    one query parameter apart. Without it a `/v1/shapes` nobody registered
    answers the same 404 and this passes, proving the parameter checked and
    the route absent at the same time.
    """
    await _refused(uow, container, LAPTOP)

    answered = await client.get("/v1/shapes", params={"device_id": LAPTOP.value})
    as_the_tenant = await client.get("/v1/shapes")

    assert answered.status_code == 404
    assert as_the_tenant.status_code == 200
    assert as_the_tenant.json()["shapes"], "the refusal is not a downgrade to this answer"


async def test_naming_no_browser_at_all_is_the_tenant_and_not_a_refusal(
    client: httpx.AsyncClient, proven: Workflow
) -> None:
    """`?device_id=` with nothing after it, and `?device_id=%20`.

    Both are the tenant asking, not a browser -- and neither is a 422 about an
    id the domain would not build. `not device_id` was doing the first and
    `DeviceId(" ")` was doing the second; a blank is normalised now, so there
    is one answer to "no browser named" however the query spells it.
    """
    plain = await client.get("/v1/shapes")
    blank = await client.get("/v1/shapes", params={"device_id": ""})
    spaces = await client.get("/v1/shapes", params={"device_id": " "})

    assert plain.json()["shapes"], "the plant never reached the store"
    assert blank.status_code == spaces.status_code == 200
    assert blank.json() == spaces.json() == plain.json()


async def test_a_blank_browser_with_a_secret_is_still_refused(
    client: httpx.AsyncClient, proven: Workflow
) -> None:
    """The other half of the normalisation: blank is "no browser named", and a
    secret with no browser named is half a pair, which is a 404 and not the
    tenant.

    Asked twice off the same blank id, the header the only difference, so what
    is being read is the header rather than a route that answers 404 to
    everything -- including one that was never registered.
    """
    answered = await client.get(
        "/v1/shapes", params={"device_id": " "}, headers={"X-Device-Secret": HERS}
    )
    without = await client.get("/v1/shapes", params={"device_id": " "})

    assert answered.status_code == 404
    assert without.status_code == 200
    assert without.json()["shapes"], "the blank id is refused with a secret and served without one"


# --- whose list it is -----------------------------------------------------


async def test_another_tenants_credential_is_served_its_own_nothing(
    container: _FakeContainer, proven: Workflow
) -> None:
    """The tenant comes off the credential and never off a literal. Two
    tenants, because a route that hardcoded `acme` would pass every
    single-tenant assertion in this file."""
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for(tenant='rival')}"},
    ) as rival:
        answered = await rival.get("/v1/shapes")

    assert answered.status_code == 200
    assert answered.json() == {"shapes": []}, "another tenant's proven job was served"
