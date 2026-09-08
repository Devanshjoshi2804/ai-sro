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
from sro.application.capture.devices import ReadRoster, RestoreDevice, RevokeDevice
from sro.application.context import RequestContext
from sro.application.skill.record_offer import RecordOffer
from sro.application.skill.serve_shapes import ServeShapes
from sro.container import Container
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId
from sro.domain.skill.workflow import Workflow
from sro.infrastructure.agent.drivers import RemoteAgents
from tests.unit.fakes import FakeClock, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer

FROZEN = datetime(2026, 3, 4, 9, 30, tzinfo=UTC)
"""Fixed, and deliberately not "today". Both module functions below turn `now`
into a rule -- a shape's rest window, an offer's clamped instant -- so a
fixture dated by the calendar is a suite that passes because of the day it ran.
The gap between this and the wall clock is also what makes the "container read
`datetime.now`" mutation die."""

RIVAL = RequestContext(tenant_id=TenantId("rival"), principal_id=PrincipalId("clerk"))
"""Deliberately not `acme`, which every other fixture in the suite uses: a
use case that read a tenant off a literal instead of off the context would
agree with `acme` by coincidence."""


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
    assert revoke._uow is uow
    assert audit._uow is uow
    # The type is not the seam; the socket registry is. A container that built
    # `RemoteAgents(DeviceSockets())` -- a driver over a fresh, empty registry
    # nobody else ever writes to -- is a `RemoteAgents` and passes an isinstance
    # check, and it breaks exactly the two things these use cases exist to
    # promise: every browser on the roster reads `online=False`, and a revoked
    # browser KEEPS ITS COMMAND CHANNEL because `drop` is a silent no-op. Both
    # survived the whole 2193-test suite until this line.
    # The isinstance is the narrowing that lets the next line be typed, not the
    # assertion: `AgentDrivers` is a Protocol and has no registry on it.
    assert isinstance(roster._drivers, RemoteAgents)
    assert isinstance(revoke._drivers, RemoteAgents)
    assert roster._drivers._sockets is container.agent_sockets
    assert revoke._drivers._sockets is container.agent_sockets
    # Not merely "a clock": the container's own, or a revocation is stamped
    # with an instant no test can move.
    assert revoke._clock is container.clock

    # The un-revoke, which is built from the unit of work alone. A container
    # that handed it `self.agents()` too would be the first step towards a
    # restore that dialled a laptop nobody is sitting at.
    restore = container.restore_device()
    assert isinstance(restore, RestoreDevice)
    # Everything it holds, not "it holds no attribute spelled `_drivers`":
    # `self._agents = self.agents()` would satisfy a spelling check and dial a
    # laptop nobody is sitting at on every press.
    assert vars(restore) == {"_uow": uow}


def test_the_container_builds_serve_shapes_from_its_own_parts(
    container: Container, uow: FakeUnitOfWork
) -> None:
    served = container.serve_shapes()

    assert isinstance(served, ServeShapes)
    # The whole of what it was built from, not merely that the two it needs are
    # right. `restore_device` three factories above guards the same thing with
    # `not hasattr(..., "_drivers")`; this is that assertion in the form a
    # renamed parameter cannot walk past. `ServeShapes` is the every-page poll,
    # and a container that handed it `self.agents()` would put a socket
    # registry behind the one read a browser makes on every gesture cache miss.
    #
    # `_clock` by identity and not merely "a clock", which is also why this is a
    # factory rather than a `ServeShapes()` a route could build: a use case
    # holding a clock of its own rests every job by the wall calendar, and no
    # test can move that.
    assert vars(served) == {"_uow": uow, "_clock": container.clock}


async def test_serve_shapes_is_asked_with_the_asking_browser_and_the_containers_clock(
    container: Container, uow: FakeUnitOfWork, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}
    monkeypatch.setattr("sro.application.skill.serve_shapes.shapes_for", _spy(seen, []))

    assert await container.serve_shapes().execute(RIVAL, device_id=DeviceId("dev_7")) == []

    assert seen["uow"] is uow
    # Off the context and never a literal: this is the seam where serving the
    # wrong tenant is one substitution away, so the tenant asserted here is
    # deliberately not the one every other fixture in the suite uses.
    assert seen["tenant_id"] == TenantId("rival")
    # The one that matters most: `device_id` decides whose refusals earned the
    # rest, so dropping it serves one browser the rest another browser earned.
    assert seen["device_id"] == DeviceId("dev_7")
    assert seen["now"] == FROZEN


async def test_serve_shapes_reaches_the_real_function_and_commits_nothing(
    container: Container, uow: FakeUnitOfWork
) -> None:
    """No spy: the import is real and a tenant with nothing proven gets [].

    Also the shape of a request no browser proved itself for -- `device_id` is
    allowed to be `None` and the tenant is answered anyway.

    And the promise `shapes_for` makes in its own docstring and nothing has
    ever held it to: "nothing writes, so nothing commits -- the caller owns the
    session". This is the read every browser makes on every gesture cache miss,
    answered inside a request that may be holding writes nobody has finished, so
    a commit here flushes somebody else's half-done work.
    """
    assert await container.serve_shapes().execute(RIVAL, device_id=None) == []

    assert uow.commits == 0


def test_the_container_builds_record_offer_from_its_own_parts(
    container: Container, uow: FakeUnitOfWork
) -> None:
    """The write door of phase 4a, and a factory rather than the container
    method it replaces: that one took a bare `tenant_id`, so the route would
    have unpacked the caller itself at the one seam where passing the wrong
    tenant is the failure.

    `vars` and not two `is` checks, for `serve_shapes`' reason above: a
    renamed parameter walks past a spelling check, and a `RecordOffer` built
    over a unit of work nobody else writes to records offers into a session
    that is never read.
    """
    recording = container.record_offer()

    assert isinstance(recording, RecordOffer)
    # `_clock` by identity: `clamped` holds the browser's reading against this
    # one, and a use case that read a clock of its own is one no test can move.
    assert vars(recording) == {"_uow": uow, "_clock": container.clock}


async def test_record_offer_clamps_the_browsers_clock_against_the_containers(
    container: Container, uow: FakeUnitOfWork
) -> None:
    """No spy, and the rule the clock buys: a browser ten months fast would
    otherwise own the rest window until 2027. The row carries ours.

    Asked as `rival`, and the job is `rival`'s: the tenant the row is written
    under comes off the context, and a use case reading a literal `acme`
    refuses this as an unknown workflow instead.
    """
    await uow.workflows.save(
        Workflow(id="wf_1", tenant="rival", title="a job of theirs", narrative="")
    )

    stored = await container.record_offer().execute(
        RIVAL,
        workflow_id="wf_1",
        device_id=DeviceId("dev_7"),
        k=3,
        fate="dismissed",
        run_id=None,
        at="2027-01-01T00:00:00+00:00",
    )

    assert stored.at == FROZEN.isoformat()
    assert stored.tenant == "rival"
    # And it is the row the store kept, not only the object handed back: this
    # is the window `counsel` reads to decide a job has earned a rest.
    window = await uow.offers.newest(TenantId("rival"), "wf_1", limit=5)
    assert [row.at for row in window] == [FROZEN.isoformat()]
