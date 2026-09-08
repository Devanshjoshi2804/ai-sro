"""The composition root hands out what the routers ask for.

Thin by design: what is worth holding is that each factory exists, returns the
type its router annotates, and is given the container's own clock, drivers and
unit of work rather than making its own. A use case built with a different
clock is one a test cannot move, and a route that reads a clock is a route with
a rule in it.

Every factory here is a call site nobody else checks. Python will build
``ReadRoster(drivers, uow)`` as happily as ``ReadRoster(uow, drivers)`` and
``shapes_for`` will serve a whole tenant's rest to a browser that earned none
of it if ``device_id`` is dropped on the way in -- so the arguments are
asserted one by one, not merely the types that come back.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from sro.application.analytics.audit import ReadAudit
from sro.application.capture.devices import ReadRoster, RevokeDevice
from sro.container import Container
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.infrastructure.agent.drivers import RemoteAgents
from tests.unit.fakes import FakeClock, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer

FROZEN = datetime(2026, 3, 4, 9, 30, tzinfo=UTC)
"""Fixed, and deliberately not "today". Both module functions below turn `now`
into a rule -- a shape's rest window, an offer's clamped instant -- so a
fixture dated by the calendar is a suite that passes because of the day it ran.
The gap between this and the wall clock is also what makes the "container read
`datetime.now`" mutation die."""


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> Container:
    """Production's own factories over in-memory adapters.

    `_FakeContainer` subclasses `Container` and overrides only `unit_of_work`,
    which is exactly what wiring wants tested: the factories under test are the
    ones a deployment runs.
    """
    built = _FakeContainer(uow)
    built.clock = FakeClock(FROZEN)
    return built


def _spy(seen: dict[str, Any], answer: object) -> Callable[..., Awaitable[Any]]:
    """Stands in for a module function and records every argument it was given.

    A spy rather than a real call because the point of these two is the
    argument list: what reaches `now` cannot be read back off a `Shape`, and an
    argument silently swapped with its neighbour is invisible in the answer.
    """

    async def recorder(unit: object, **kwargs: object) -> object:
        seen["uow"] = unit
        seen.update(kwargs)
        return answer

    return recorder


def test_the_container_builds_the_phase_three_use_cases(
    container: Container, uow: FakeUnitOfWork
) -> None:
    roster = container.read_roster()
    revoke = container.revoke_device()
    audit = container.read_audit()

    assert isinstance(roster, ReadRoster)
    assert isinstance(revoke, RevokeDevice)
    assert isinstance(audit, ReadAudit)

    # The caller seam. `uow` and `drivers` are adjacent positional parameters
    # of two of these, so a swap builds cleanly and only fails in production.
    assert roster._uow is uow
    assert isinstance(roster._drivers, RemoteAgents)
    assert revoke._uow is uow
    assert isinstance(revoke._drivers, RemoteAgents)
    assert audit._uow is uow
    # Not merely "a clock": the container's own, or a revocation is stamped
    # with an instant no test can move.
    assert revoke._clock is container.clock


async def test_shapes_is_asked_with_the_asking_browser_and_the_containers_clock(
    container: Container, uow: FakeUnitOfWork, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}
    monkeypatch.setattr("sro.container.shapes_for", _spy(seen, []))

    assert await container.shapes(TenantId("acme"), DeviceId("dev_7")) == []

    assert seen["uow"] is uow
    assert seen["tenant_id"] == TenantId("acme")
    # The one that matters most: `device_id` decides whose refusals earned the
    # rest, so dropping it serves one browser the rest another browser earned.
    assert seen["device_id"] == DeviceId("dev_7")
    assert seen["now"] == FROZEN


async def test_shapes_reaches_the_real_function(container: Container) -> None:
    """No spy: the import is real and a tenant with nothing proven gets [].

    Also the shape of a request no browser proved itself for -- `device_id` is
    allowed to be `None` and the tenant is answered anyway.
    """
    assert await container.shapes(TenantId("acme"), None) == []


async def test_record_offer_is_given_every_argument_and_the_containers_clock(
    container: Container, uow: FakeUnitOfWork, monkeypatch: pytest.MonkeyPatch
) -> None:
    sentinel = object()
    seen: dict[str, Any] = {}
    monkeypatch.setattr("sro.container.record_offer", _spy(seen, sentinel))

    got = await container.record_offer(
        tenant_id=TenantId("acme"),
        workflow_id="wf_1",
        device_id=DeviceId("dev_7"),
        k=3,
        fate="dismissed",
        run_id="run_9",
        at="2027-01-01T00:00:00+00:00",
    )

    assert got is sentinel
    # Eight arguments, all keyword and several of them strings, so a
    # cross-wiring here type-checks and stores somebody else's offer.
    assert seen["uow"] is uow
    assert seen["tenant_id"] == TenantId("acme")
    assert seen["workflow_id"] == "wf_1"
    assert seen["device_id"] == DeviceId("dev_7")
    assert seen["k"] == 3
    assert seen["fate"] == "dismissed"
    assert seen["run_id"] == "run_9"
    assert seen["at"] == "2027-01-01T00:00:00+00:00"
    assert seen["now"] == FROZEN


async def test_record_offer_clamps_the_browsers_clock_against_the_containers(
    container: Container, uow: FakeUnitOfWork
) -> None:
    """No spy, and the rule the clock buys: a browser ten months fast would
    otherwise own the rest window until 2027. The row carries ours."""
    stored = await container.record_offer(
        tenant_id=TenantId("acme"),
        workflow_id="wf_1",
        device_id=DeviceId("dev_7"),
        k=3,
        fate="dismissed",
        run_id=None,
        at="2027-01-01T00:00:00+00:00",
    )

    assert stored.at == FROZEN.isoformat()
    # And it is the row the store kept, not only the object handed back: this
    # is the window `counsel` reads to decide a job has earned a rest.
    window = await uow.offers.newest(TenantId("acme"), "wf_1", limit=5)
    assert [row.at for row in window] == [FROZEN.isoformat()]
