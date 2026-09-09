"""`POST /v1/offers` -- the one door in phase 4a that writes.

Ported from `new_agent_arch/src/rig/api.py:1548`. What the extension showed an
operator and what they did with it: the labelled record `counsel` reads to
decide what a job is offered at, and when a job somebody refused three times
running is offered again.

Every test here reads the row back through `/v1/audit` rather than trusting
the status code. That is the whole difference between this route and the four
reads beside it: a 201 says a request was accepted, and what has to be true is
that a REFUSED body left nothing behind. A route that recorded first and
validated afterwards answers 400 and stores the row, and every assertion on a
status code agrees with it.

The browser is named by the secret it proves itself with and never by the
body, so one test posts a `device_id` in the body and asserts the stored row
carries the browser that asked instead. `?device_id=` plus `X-Device-Secret`
is the only pair `asking_device` accepts: a secret with no id named, or an id
with no secret, is a half-pair refused as a 404 before this route is reached.

Nothing here is dated today. The container's clock reads `f.T0` -- March
2026, six months from the wall clock -- and every browser reading is planted
against it, so a route that dropped `at` and stamped its own instant cannot
agree with a fixture by the calendar.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from httpx import ASGITransport

from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.workflow import Step, Workflow
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LAPTOP = DeviceId("dev-1")
HERS = "the-secret-the-laptop-was-minted"

RIVALS = DeviceId("dev-9")
THEIRS = "the-secret-the-rivals-laptop-was-minted"

JOB = "wfl_zebra"
"""`acme`'s job, and the one every test below offers."""

TRAVELLED = "wfl_alpha"
"""`rival`'s job, and `acme` has no such thing.

The workflow lookup is tenant-scoped, and this is both halves of that: `acme`
naming it is refused even though the row exists, and `rival` offering it is
recorded -- into `rival`'s audit, which is where a route holding a literal
`acme` shows.
"""

SHOWN_AT = f.at(-1800)
"""The browser's own reading: half an hour before the container's clock.

In the past on purpose. `clamped` keeps the earlier of the two instants, so
this is the value that survives -- and a route that dropped `at` would stamp
`f.T0` instead, which is a different string.
"""

SINCE = f.at(-7200).isoformat()
"""The audit window every read-back below asks over: wide enough to hold
`SHOWN_AT` and the container's clock both, so a row that was written is never
missed for being outside it."""


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    return _FakeContainer(uow)


def _client(container: _FakeContainer, *, tenant: str = "") -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    return httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for(tenant=tenant)}"},
    )


@pytest.fixture
async def client(container: _FakeContainer) -> AsyncIterator[httpx.AsyncClient]:
    async with _client(container) as http:
        yield http


@pytest.fixture
async def rival(container: _FakeContainer) -> AsyncIterator[httpx.AsyncClient]:
    """A second tenant's credential against the same container.

    A route that hardcoded `acme` -- or read the tenant off anything but `ctx`
    -- passes every other assertion in this file.
    """
    async with _client(container, tenant="rival") as http:
        yield http


@pytest.fixture(autouse=True)
async def planted(uow: FakeUnitOfWork) -> None:
    """Two tenants, a browser each, and the jobs above."""
    await uow.devices.add(f.device(id=LAPTOP, secret=HERS))
    await uow.devices.add(
        f.device(id=RIVALS, secret=THEIRS, tenant_id=TenantId("rival"), label="theirs")
    )
    await uow.workflows.save(_workflow(JOB, tenant="acme"))
    await uow.workflows.save(_workflow(TRAVELLED, tenant="rival"))


def _workflow(workflow_id: str, *, tenant: str) -> Workflow:
    return Workflow(
        id=workflow_id,
        tenant=tenant,
        title=f"create a client ({tenant})",
        narrative="open the client screen, type the code, save",
        systems=["wms.test"],
        steps=[Step(order=0, says="open the client screen", system="wms.test", cites=["ges-1"])],
    )


def _offered(**overrides: object) -> dict[str, object]:
    """A whole offer, every field carrying something a default could not be.

    `k` is 7 and not 0, `run_id` names a run and is not `None`, and the fate is
    one no other test in this file uses: each of those is a value a response
    model that blanked the field, or a route that dropped the argument, would
    otherwise agree with.
    """
    body: dict[str, object] = {
        "workflow_id": JOB,
        "fate": "diverged",
        "k": 7,
        "run_id": "run-42",
        "at": SHOWN_AT.isoformat(),
    }
    return body | overrides


def _as(device: DeviceId, secret: str) -> dict[str, Any]:
    """The two halves `asking_device` needs, together: the id in the query
    string, the secret in the header. Either alone is a 404."""
    return {"params": {"device_id": device.value}, "headers": {"X-Device-Secret": secret}}


async def _offers(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    """What this tenant's audit says was offered. The read-back, and the only
    thing in this file that can tell a refusal that wrote nothing from one
    that wrote a row and then said no."""
    answered = await client.get("/v1/audit", params={"since": SINCE})
    assert answered.status_code == 200, answered.text
    offers: list[dict[str, Any]] = answered.json()["offers"]
    return offers


# --- the offer a browser made ----------------------------------------------


async def test_a_browser_records_the_offer_it_showed(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """Every field of the body reaches the row, and the row is committed."""
    answered = await client.post("/v1/offers", json=_offered(), **_as(LAPTOP, HERS))

    assert answered.status_code == 201, answered.text
    assert answered.json()["offer_id"].startswith("off_")

    # Read back whole, not field by field: a route that dropped one argument,
    # or a model that blanked one, is a different dict from this one.
    assert await _offers(client) == [
        {
            "id": answered.json()["offer_id"],
            "workflow_id": JOB,
            # The browser that proved itself, which is the only thing that
            # names it.
            "device_id": LAPTOP.value,
            "k": 7,
            "fate": "diverged",
            "run_id": "run-42",
            # The BROWSER's reading, not the server's: dropping `at` stamps
            # `f.T0` here instead, which this is deliberately not.
            "at": SHOWN_AT.isoformat(),
        }
    ]
    # The row is written inside a transaction that ends. Nothing else in this
    # file would notice a missing commit: the fake's repositories hold what
    # they were handed either way, and Postgres would throw the offer away.
    assert uow.commits == 1


async def test_an_arrival_nudge_is_an_offer_at_k_zero(client: httpx.AsyncClient) -> None:
    """`k=0` is the "you have been here before" nudge, and is a real offer.

    Zero is the value a route that dropped `k` would produce by accident, so
    it is asserted here beside the k=7 above rather than only here: this test
    says a nudge is accepted, and that one says a k is carried.
    """
    answered = await client.post(
        "/v1/offers", json=_offered(k=0, fate="expired", run_id=None), **_as(LAPTOP, HERS)
    )

    assert answered.status_code == 201, answered.text
    assert [(offer["k"], offer["fate"], offer["run_id"]) for offer in await _offers(client)] == [
        (0, "expired", None)
    ]


async def test_the_browser_that_proved_itself_is_the_one_recorded(
    client: httpx.AsyncClient,
) -> None:
    """A `device_id` in the body names nobody.

    The rig read one out of the body. A job's rest is per browser, so a body
    that could name another browser could spend a colleague's rest or earn it.
    """
    answered = await client.post(
        "/v1/offers", json=_offered(device_id="dev-someone-else"), **_as(LAPTOP, HERS)
    )

    assert answered.status_code == 201, answered.text
    assert [offer["device_id"] for offer in await _offers(client)] == [LAPTOP.value]


async def test_a_browser_ahead_of_the_server_does_not_own_the_window(
    client: httpx.AsyncClient,
) -> None:
    """`clamped`, through the route: the row carries our clock, never theirs.

    A browser ten months fast would otherwise rest the job it refused until
    2027, on every browser that reads the counsel after it.
    """
    answered = await client.post(
        "/v1/offers", json=_offered(at="2027-01-01T00:00:00+00:00"), **_as(LAPTOP, HERS)
    )

    assert answered.status_code == 201, answered.text
    assert [offer["at"] for offer in await _offers(client)] == [f.T0.isoformat()]


async def test_a_browser_that_reported_no_clock_is_stamped_with_ours(
    client: httpx.AsyncClient,
) -> None:
    """`at` is optional, and absent it is the container's clock and not one the
    route read: which day an offer falls on decides when its job comes back."""
    body = _offered()
    del body["at"]

    answered = await client.post("/v1/offers", json=body, **_as(LAPTOP, HERS))

    assert answered.status_code == 201, answered.text
    assert [offer["at"] for offer in await _offers(client)] == [f.T0.isoformat()]


# --- what is refused, and what it leaves behind ------------------------------


async def test_a_job_this_tenant_does_not_have_is_refused_and_writes_nothing(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    answered = await client.post(
        "/v1/offers", json=_offered(workflow_id="wfl_nope"), **_as(LAPTOP, HERS)
    )

    assert answered.status_code == 400, answered.text
    assert "wfl_nope" not in answered.text, "the refusal echoed the body into the log"
    assert await _offers(client) == []
    assert uow.commits == 0


async def test_a_job_only_the_other_tenant_has_is_a_job_this_one_does_not_have(
    client: httpx.AsyncClient,
) -> None:
    """The lookup is tenant-scoped. A workflow id that exists is not the
    question; whose it is, is."""
    answered = await client.post(
        "/v1/offers", json=_offered(workflow_id=TRAVELLED), **_as(LAPTOP, HERS)
    )

    assert answered.status_code == 400, answered.text
    assert await _offers(client) == []


async def test_a_fate_that_is_not_one_is_refused_and_writes_nothing(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """A fate nothing recognises is neither a refusal nor an acceptance -- it
    is a row `counsel` reads as neither for as long as it stays in the
    window."""
    answered = await client.post("/v1/offers", json=_offered(fate="maybe"), **_as(LAPTOP, HERS))

    assert answered.status_code == 400, answered.text
    assert "maybe" not in answered.text, "the refusal echoed the body into the log"
    # Said forwards, so the caller can fix it without being read their own
    # string back.
    assert "dismissed" in answered.json()["detail"]
    assert await _offers(client) == []
    assert uow.commits == 0


@pytest.mark.parametrize("k", [-1, True, 1.5, "3"])
async def test_a_k_that_is_not_a_count_is_refused_and_writes_nothing(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, k: object
) -> None:
    """`True` is an `int` in Python and pydantic coerces it: `{"k": true}`
    would be stored as a tail that matched one gesture because the language
    says so and not because anything matched. The rig hit this on `from_step`.
    """
    answered = await client.post("/v1/offers", json=_offered(k=k), **_as(LAPTOP, HERS))

    assert answered.status_code == 422, f"k={k!r} was accepted"
    assert await _offers(client) == []
    assert uow.commits == 0


# --- who may record one ------------------------------------------------------


async def test_the_tenants_own_credential_records_no_offer(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The caller, not only the rule. An offer is a browser's: recorded with
    no browser named it is evidence about a shift nobody worked, and it would
    share one rest window with every other unnamed offer."""
    answered = await client.post("/v1/offers", json=_offered())

    assert answered.status_code == 403, answered.text
    assert await _offers(client) == []
    assert uow.commits == 0


async def test_a_secret_with_no_browser_named_records_no_offer(
    client: httpx.AsyncClient,
) -> None:
    """Half a pair is a refusal and never a downgrade to the tenant. 404, and
    it is `asking_device`'s, reached before this route's own rule."""
    answered = await client.post("/v1/offers", json=_offered(), headers={"X-Device-Secret": HERS})

    assert answered.status_code == 404, answered.text
    assert await _offers(client) == []


async def test_a_browser_of_another_tenant_is_not_this_tenants_browser(
    client: httpx.AsyncClient,
) -> None:
    """`acme`'s credential naming `rival`'s browser: the device lookup is
    tenant-scoped, and absent, wrong and somebody else's are one answer."""
    answered = await client.post("/v1/offers", json=_offered(), **_as(RIVALS, THEIRS))

    assert answered.status_code == 404, answered.text
    assert await _offers(client) == []


# --- whose offer it is -------------------------------------------------------


async def test_the_offer_is_written_under_the_asking_tenant(
    client: httpx.AsyncClient, rival: httpx.AsyncClient
) -> None:
    """The other tenant's browser, offering the other tenant's job.

    A route holding a literal `acme` -- or reading the tenant off anything but
    the credential -- refuses this as an unknown workflow, or takes it and
    puts the row in the wrong tenant's audit. Both halves are asserted: the
    row is in `rival`'s, and `acme`'s is still empty.
    """
    answered = await rival.post(
        "/v1/offers", json=_offered(workflow_id=TRAVELLED), **_as(RIVALS, THEIRS)
    )

    assert answered.status_code == 201, answered.text
    assert [offer["device_id"] for offer in await _offers(rival)] == [RIVALS.value]
    assert await _offers(client) == []
