"""Cutting a browser off: the row and the socket, which are one act.

Ported from the use-case half of `new_agent_arch/tests/test_devices.py`. The
rig's `issue` and `holder` have no port here -- `RegisterDevice` and
`AgentDevice.proves_itself` already answered both before the rig arrived, and
`tests/unit/application/test_an_extension_uploads_what_it_saw.py` covers them
-- so what is left of that file's thirteen tests, once the route-level ones go
to phase 4, is the revoke and the roster it is read against.

Every test here mutates the *arguments* as well as the rule. The repository
write and the socket drop each take a tenant and a device, and sending either
the wrong one is the defect: a revoke that cuts off the browser next to the
one that was asked for is green against any assertion made only on the
returned boolean.
"""

from __future__ import annotations

import pytest

from sro.application.capture.devices import ReadRoster, RevokeDevice
from sro.application.context import RequestContext
from sro.application.observation.register import RecordHeartbeat, RegisterDevice
from sro.domain.observation.device import AgentDevice
from sro.domain.shared.errors import Conflict, NotFound
from sro.domain.shared.identifiers import DeviceId, TenantId
from tests import factories as f
from tests.unit.fakes import FakeAgentDrivers, FakeClock, FakeIdFactory, FakeUnitOfWork

ACME = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
OTHER = RequestContext(tenant_id=TenantId("other-corp"), principal_id=f.OPERATOR)

LAPTOP = DeviceId("dev-1")
DESKTOP = DeviceId("dev-2")
THEIRS = DeviceId("dev-3")
"""Another tenant's browser. A different id from this tenant's, because the
store keys devices by id and two tenants holding one id is a shape neither the
fake nor Postgres has -- what is under test is a *call* naming the wrong
tenant, not a collision."""


class _Drivers(FakeAgentDrivers):
    """`FakeAgentDrivers` with a memory for who it was asked about.

    Its `drop` answers correctly and forgets its arguments, and the arguments
    are the defect this file exists to catch. Subclassed rather than changed:
    `tests/unit/fakes.py` is shared, and a browser dropped on the wrong tenant
    is a fact only a recording double can see.
    """

    def __init__(self, *connected: DeviceId) -> None:
        super().__init__()
        self.connected_devices: tuple[DeviceId, ...] = connected
        self.dropped: list[tuple[str, str]] = []
        self.asked_online: list[str] = []

    def reconnect(self, *devices: DeviceId) -> None:
        """A browser that came back after its revocation, or one another
        administrator revoked while this socket was still open."""
        self.connected_devices = devices

    async def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]:
        self.asked_online.append(tenant_id.value)
        return self.connected_devices

    def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        self.dropped.append((tenant_id.value, device_id.value))
        was_open = device_id in self.connected_devices
        self.connected_devices = tuple(held for held in self.connected_devices if held != device_id)
        return was_open


async def _known(*devices: AgentDevice) -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    for device in devices:
        await uow.devices.add(device)
    return uow


async def test_a_browser_is_revoked_once_and_the_second_press_moves_nothing() -> None:
    """The rig's `revoke(store, "dev_1") is True and revoke(...) is False`, and
    the half it did not state: the instant the first press recorded is what an
    audit of what this browser was allowed to do is read against, so a second
    press an hour later must leave it exactly where it was."""
    uow = await _known(f.device(id=LAPTOP))
    clock = FakeClock()
    revoke = RevokeDevice(uow, _Drivers(LAPTOP), clock)

    assert await revoke.execute(ACME, device_id=LAPTOP) is True
    ended = (await uow.devices.get(f.TENANT, LAPTOP)).revoked_at
    assert ended == clock.now().isoformat()

    clock.advance(3600)
    assert await revoke.execute(ACME, device_id=LAPTOP) is False
    assert (await uow.devices.get(f.TENANT, LAPTOP)).revoked_at == ended
    assert uow.commits == 2, "and each press was written, not left in the session"


async def test_a_revoked_browser_is_refused_the_moment_it_speaks_again() -> None:
    """The whole point of the revocation, and the half a row alone does not
    make true.

    The rig's `holder` filtered `revoked_at IS NULL`, so a revoked token
    belonged to nobody. Here the gate is `refuse_unless_itself`, and revoking
    deliberately leaves the secret alone -- a device with no secret cannot be
    told from one registered before secrets existed -- so a gate that asked
    only "is this the browser that registered" answers yes forever and the
    extension resumes on its next heartbeat holding the same credential.

    Asked through the heartbeat because that is the call a cut-off browser
    makes next; the gate is shared by all seven device-scoped paths, which is
    why it is fixed there and checked once.
    """
    uow = FakeUnitOfWork()
    registered = await RegisterDevice(uow, FakeClock(), FakeIdFactory()).execute(
        ACME, label="laptop", extension_version="0.1.0"
    )
    beat = RecordHeartbeat(uow, FakeClock())
    await beat.execute(ACME, device_id=registered.device_id, secret=registered.secret)

    await RevokeDevice(uow, _Drivers(), FakeClock()).execute(ACME, device_id=registered.device_id)

    with pytest.raises(NotFound):
        await beat.execute(ACME, device_id=registered.device_id, secret=registered.secret)


async def test_a_revocation_that_did_not_commit_cuts_nobody_off() -> None:
    """The drop is after the commit, and this is the difference that makes.
    A browser cut off for a revocation the store then refused is an operator
    whose extension stopped for no recorded reason -- and nothing would ever
    say why, because the row that would have explained it was rolled back.
    """
    uow = await _known(f.device(id=LAPTOP))
    uow.commit_raises = Conflict("dev-1 was written by somebody else")
    drivers = _Drivers(LAPTOP)

    with pytest.raises(Conflict):
        await RevokeDevice(uow, drivers, FakeClock()).execute(ACME, device_id=LAPTOP)

    assert drivers.dropped == []
    assert drivers.connected_devices == (LAPTOP,)


async def test_revoking_a_browser_takes_it_offline_at_once() -> None:
    """The rig's name, and its assertion: `channel.online() == []` the moment
    the revocation answers, not whenever the socket happens to drop. A row that
    says revoked beside a channel still taking commands is the audit line
    `AgentDrivers.drop` exists to prevent."""
    uow = await _known(f.device(id=LAPTOP))
    drivers = _Drivers(LAPTOP)

    await RevokeDevice(uow, drivers, FakeClock()).execute(ACME, device_id=LAPTOP)

    assert drivers.dropped == [("acme", "dev-1")]
    assert drivers.connected_devices == ()
    [line] = await ReadRoster(uow, drivers).execute(ACME)
    assert line.online is False and line.device.revoked is True


async def test_the_socket_is_cut_even_when_there_was_no_live_token_left() -> None:
    """The rig dropped on every press, not only on the press that changed a
    row, and it is the only caller that can. A browser revoked a minute ago by
    somebody else -- or one that reconnected after its revocation -- is holding
    a socket that nothing else will close, and "there was a live token" is a
    different question from "is one still connected"."""
    uow = await _known(f.device(id=LAPTOP))
    drivers = _Drivers()
    revoke = RevokeDevice(uow, drivers, FakeClock())

    assert await revoke.execute(ACME, device_id=LAPTOP) is True
    drivers.reconnect(LAPTOP)

    assert await revoke.execute(ACME, device_id=LAPTOP) is False, "the row was already revoked"
    assert drivers.dropped == [("acme", "dev-1"), ("acme", "dev-1")]
    assert drivers.connected_devices == (), "and the second press still cut it"


async def test_a_browser_of_another_tenant_is_neither_revoked_nor_dropped() -> None:
    """`NotFound`, not a quiet `False`: "no such browser" and "nothing live to
    revoke" are different answers, and a revoke that softened the first would
    let a tenant confirm another tenant's device ids by pressing at them."""
    uow = await _known(f.device(id=LAPTOP), f.device(id=THEIRS, tenant_id=OTHER.tenant_id))
    drivers = _Drivers(LAPTOP, THEIRS)
    revoke = RevokeDevice(uow, drivers, FakeClock())

    with pytest.raises(NotFound):
        await revoke.execute(OTHER, device_id=LAPTOP)
    with pytest.raises(NotFound):
        await revoke.execute(ACME, device_id=THEIRS)

    assert (await uow.devices.get(f.TENANT, LAPTOP)).revoked is False
    assert (await uow.devices.get(OTHER.tenant_id, THEIRS)).revoked is False
    assert drivers.dropped == [], "nothing was cut off on a revocation that did not happen"


async def test_the_row_and_the_socket_name_the_browser_that_was_asked_for() -> None:
    """Both halves take a tenant and a device, and the sibling browser is the
    thing that goes wrong: an operator's own laptop cut off because somebody
    revoked the desktop beside it."""
    uow = await _known(f.device(id=LAPTOP), f.device(id=DESKTOP))
    drivers = _Drivers(LAPTOP, DESKTOP)

    await RevokeDevice(uow, drivers, FakeClock()).execute(ACME, device_id=DESKTOP)

    assert (await uow.devices.get(f.TENANT, DESKTOP)).revoked is True
    assert (await uow.devices.get(f.TENANT, LAPTOP)).revoked is False
    assert drivers.dropped == [("acme", "dev-2")]
    assert drivers.connected_devices == (LAPTOP,)


async def test_a_revoked_browser_stays_on_the_roster_carrying_when_it_ended() -> None:
    """The rig's `registered` list: "the list the tenant reads before cutting
    one off, and after". A revocation that erased its own subject would leave
    an administrator unable to confirm the thing they had just done."""
    ended = f.at(600).isoformat()
    uow = await _known(f.device(id=LAPTOP, revoked_at=ended), f.device(id=DESKTOP))

    roster = await ReadRoster(uow, _Drivers()).execute(ACME)

    assert {line.device.id: line.device.revoked_at for line in roster} == {
        LAPTOP: ended,
        DESKTOP: None,
    }


async def test_a_revoked_browser_never_reads_as_online() -> None:
    """Even holding a socket. `RevokeDevice` drops it, so normally there is
    nothing to report -- but the row is the authority and the socket is a fact
    about a wire, and a browser whose drop was missed reading as connected on
    the list an administrator answers "who can act" from is the whole of what
    that drop was for."""
    uow = await _known(f.device(id=LAPTOP, revoked_at=f.at(600).isoformat()))

    [line] = await ReadRoster(uow, _Drivers(LAPTOP)).execute(ACME)

    assert line.device.revoked is True
    assert line.online is False


async def test_the_roster_is_this_tenants_browsers_most_recently_seen_first() -> None:
    """One tenant's, in the store's order, each with its own answer about
    being connected. The tenant is asked of the drivers too: an online list
    read for the wrong tenant would mark a browser connected because somebody
    else's is."""
    uow = await _known(
        f.device(id=LAPTOP, last_seen_at=f.at(60)),
        f.device(id=DESKTOP, last_seen_at=f.at(120)),
        f.device(id=THEIRS, tenant_id=OTHER.tenant_id, last_seen_at=f.at(180)),
    )
    drivers = _Drivers(LAPTOP, THEIRS)

    roster = await ReadRoster(uow, drivers).execute(ACME)

    assert [(line.device.id, line.online) for line in roster] == [
        (DESKTOP, False),
        (LAPTOP, True),
    ]
    assert drivers.asked_online == ["acme"]
