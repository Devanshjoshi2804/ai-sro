"""Which browser is asking, on a model the rig did not have.

The rig's `caller` read one bearer and answered "the tenant, or this device".
The backend's credential names a tenant and never a browser, so the same
question is answered by a second header -- and a route that got this wrong
would serve one browser's rest to another, or let a tenant credential
impersonate a browser by naming it in a query string.

Through the production `ReadDevice`, not a stand-in that re-states its rule: a
fake that decided for itself which (id, secret) pairs are acceptable would
still pass if `asking_device` handed it the two in the wrong order.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from sro.application.context import RequestContext
from sro.application.observation.register import ReadDevice
from sro.domain.observation.device import AgentDevice
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.interface.http.asking import asking_device, tenant_only
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer

HERS = "the-secret-this-browser-was-minted"
LAPTOP = DeviceId("dev-1")

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


class _Watched(ReadDevice):
    """The production use case, with a note of everything it was asked.

    The whole seam is one call taking three things: whose tenant, which
    browser, and what it claims to prove itself with. Swapping two of them or
    dropping one is how a browser gets served another browser's rest, and none
    of it shows up in the return value.
    """

    def __init__(self, uow: FakeUnitOfWork) -> None:
        super().__init__(uow)
        self.asked: list[tuple[str, str, str]] = []

    async def execute(
        self, ctx: RequestContext, *, device_id: DeviceId, secret: str
    ) -> AgentDevice:
        self.asked.append((ctx.tenant_id.value, device_id.value, secret))
        return await super().execute(ctx, device_id=device_id, secret=secret)


class _WatchingContainer(_FakeContainer):
    def __init__(self, uow: FakeUnitOfWork) -> None:
        super().__init__(uow)
        self.watched = _Watched(uow)

    def read_device(self) -> ReadDevice:
        return self.watched


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _WatchingContainer:
    return _WatchingContainer(uow)


@pytest.fixture
async def registered(uow: FakeUnitOfWork) -> AgentDevice:
    """One browser that really registered, under this tenant, with a secret."""
    device = f.device(id=LAPTOP, secret=HERS)
    await uow.devices.add(device)
    return device


async def test_no_secret_and_no_device_is_the_tenant_asking(
    container: _WatchingContainer,
) -> None:
    assert await asking_device(container, CTX, "", None) is None
    assert container.watched.asked == [], "a request with no device asked the repository anyway"


async def test_a_blank_device_named_is_no_device_named(
    container: _WatchingContainer, registered: AgentDevice
) -> None:
    """`?device_id=` and `?device_id=%20` are the tenant, not two other answers.

    A query string carries "" where an absent parameter carries `None`, so a
    check written `device_id is None` reads the first as a browser and refuses
    the tenant with a 404. Whitespace went further: it is truthy, so it reached
    `DeviceId(" ")`, which the domain will not build -- a 422 about the shape
    of a query string, from the one route whose whole promise is that absent,
    wrong and somebody else's are one answer.
    """
    assert await asking_device(container, CTX, "", "") is None
    assert await asking_device(container, CTX, "", " ") is None
    assert container.watched.asked == []


async def test_a_padded_id_is_not_quietly_rewritten_into_the_browser_it_resembles(
    container: _WatchingContainer, registered: AgentDevice
) -> None:
    """Blanking a whitespace-only id is not licence to trim every other one.

    `device_id.strip()` reads like the same rule and is not: it rewrites what
    the caller named on its way to `DeviceId`, at the one seam whose whole job
    is which browser was named. ` dev-1` and its real secret would then
    authenticate as `dev-1`. Refused instead, in the same words as a browser
    that does not exist -- and the store is asked for the id as it was given,
    which is the assertion that fails if the trim comes back.
    """
    with pytest.raises(HTTPException) as refused:
        await asking_device(container, CTX, HERS, f" {LAPTOP.value}")

    assert refused.value.status_code == 404
    assert container.watched.asked == [(f.TENANT.value, f" {LAPTOP.value}", HERS)]


async def test_a_browser_that_proves_itself_is_named(
    container: _WatchingContainer, registered: AgentDevice
) -> None:
    assert await asking_device(container, CTX, HERS, LAPTOP.value) == LAPTOP


async def test_the_secret_is_checked_against_the_device_that_was_named(
    container: _WatchingContainer, registered: AgentDevice
) -> None:
    # The seam: the tenant, the device and the secret all go into one call, and
    # swapping any two, or dropping one, is how a browser gets served another
    # browser's rest.
    await asking_device(container, CTX, HERS, LAPTOP.value)

    assert container.watched.asked == [(f.TENANT.value, LAPTOP.value, HERS)]


async def test_a_secret_for_another_browser_is_refused_not_downgraded(
    container: _WatchingContainer, registered: AgentDevice
) -> None:
    # Never silently "the tenant, then": a wrong secret is a request that
    # believed it was a browser, and answering it as the tenant would serve
    # every device's data to a browser that failed to prove it was one.
    with pytest.raises(HTTPException) as refused:
        await asking_device(container, CTX, "not-hers", LAPTOP.value)

    assert refused.value.status_code == 404


async def test_a_named_device_with_no_secret_is_refused(
    container: _WatchingContainer, registered: AgentDevice
) -> None:
    # A tenant credential naming a browser in a query string is not that
    # browser. Without this, `?device_id=` is an impersonation parameter.
    with pytest.raises(HTTPException) as refused:
        await asking_device(container, CTX, "", LAPTOP.value)

    assert refused.value.status_code == 404
    assert container.watched.asked == [], "half a pair reached the repository"


async def test_a_secret_with_no_device_named_is_refused(
    container: _WatchingContainer, registered: AgentDevice
) -> None:
    with pytest.raises(HTTPException) as refused:
        await asking_device(container, CTX, HERS, None)

    assert refused.value.status_code == 404
    assert container.watched.asked == []


async def test_another_tenant_holding_the_right_secret_is_still_refused(
    container: _WatchingContainer, registered: AgentDevice
) -> None:
    """The credential still decides whose browsers exist at all.

    A leaked secret must not reach across tenants, which is only true while the
    context this was asked with is the one handed to the use case.
    """
    theirs = RequestContext(tenant_id=TenantId("rival"), principal_id=f.OPERATOR)

    with pytest.raises(HTTPException) as refused:
        await asking_device(container, theirs, HERS, LAPTOP.value)

    assert refused.value.status_code == 404
    # Word for word the answer a browser that does not exist gets. A refusal
    # that said "wrong tenant" here would confirm which device ids exist to
    # anybody holding any tenant's credential and one leaked secret.
    assert str(refused.value.detail) == f"device {LAPTOP.value} was not found"


async def test_absent_wrong_and_somebody_else_s_are_one_answer(
    container: _WatchingContainer, registered: AgentDevice
) -> None:
    """The decision the module's 404 comment records, and what it costs.

    A refusal that told these apart would let anyone holding a tenant
    credential enumerate which browsers exist by reading the difference.
    """
    somebody_else = RequestContext(tenant_id=TenantId("rival"), principal_id=f.OPERATOR)
    refusals = []
    for ctx, secret, named in (
        (CTX, HERS, "dev-nobody-registered"),  # never registered
        (CTX, "not-hers", LAPTOP.value),  # registered, wrong secret
        (CTX, "", LAPTOP.value),  # registered, no secret offered at all
        (somebody_else, HERS, LAPTOP.value),  # registered to another tenant
    ):
        with pytest.raises(HTTPException) as refused:
            await asking_device(container, ctx, secret, named)
        refusals.append((refused.value.status_code, str(refused.value.detail)))

    assert refusals[0] == (404, "device dev-nobody-registered was not found")
    # Word for word, including the one that never reached a repository and the
    # one that belongs to somebody else: the difference between "wrong secret",
    # "no secret" and "not yours" is not on the wire.
    assert (
        refusals[1]
        == refusals[2]
        == refusals[3]
        == (
            404,
            f"device {LAPTOP.value} was not found",
        )
    )


# --- And what the answer is used for -------------------------------------


async def test_the_tenant_asking_is_let_through(container: _WatchingContainer) -> None:
    """`asking_device` answered `None`, so this is the tenant's own credential
    and the door opens. Ported from `new_agent_arch/src/rig/api.py:423`."""
    # Nothing raised is the assertion: `asking_device` answered `None`, so
    # there is no browser here and the door opens.
    await tenant_only(None)


async def test_a_browser_that_proved_itself_is_still_refused(
    container: _WatchingContainer, registered: AgentDevice
) -> None:
    """The other direction, and the whole point: proving you are a browser is
    exactly what gets you turned away here.

    Registering and revoking browsers, spending model money and reading every
    browser's day are the tenant's -- a browser's secret opens its own doors
    and not the tenant's purse or the other browsers' evidence. A gate that
    only refused *unproven* browsers would be no gate at all, because every
    browser holds a working secret.
    """
    asking = await asking_device(container, CTX, HERS, LAPTOP.value)

    with pytest.raises(HTTPException) as refused:
        await tenant_only(asking)

    assert refused.value.status_code == 403
    assert refused.value.detail == "that is the tenant's to do, not a browser's"


async def test_the_refusal_is_403_and_not_the_404_the_device_paths_give() -> None:
    """Deliberate, and the one place this file's 404 rule does not apply.

    The device-scoped paths hide absent, wrong and somebody else's behind one
    404 so a caller cannot enumerate browsers. Nothing is hidden here: the
    caller holds a tenant credential that was accepted and a device secret that
    checked out, so they already know the browser exists -- they proved they
    are it. A 404 would only tell them the route does not exist, which is false.
    """
    with pytest.raises(HTTPException) as refused:
        await tenant_only(LAPTOP)

    assert refused.value.status_code != 404
    assert refused.value.status_code == 403
