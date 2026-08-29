"""An extension announcing itself, and saying it is still there."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.observation.policy import current_policy
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.errors import Conflict, NotFound
from sro.domain.shared.identifiers import DeviceId


@dataclass(frozen=True, slots=True)
class Registered:
    device_id: DeviceId
    policy: ObservationPolicy
    secret: str
    """Said once, to the browser that asked, and never listed anywhere.

    Handed back on every registration rather than only the first, because
    registration is idempotent on (tenant, principal, label): a caller who can
    reach this answer is holding the credential of the operator whose device it
    is, and a reinstall that could not get its secret back would be a device
    that had to be deleted by hand to work again.
    """


@dataclass(frozen=True, slots=True)
class Beat:
    policy_version: int
    policy: ObservationPolicy | None
    """Only when the version the device holds is behind. A heartbeat that
    re-sent the whole policy every minute would be the largest thing this
    system says to a browser, and it says it once."""

    pause: bool


def refuse_unless_itself(device: AgentDevice, secret: str, asked_for: DeviceId) -> None:
    """Raise the answer a stranger gets, unless this browser proved it is itself.

    Word for word the message `DeviceRepository.get` raises for a device that
    does not exist, and deliberately: another operator's device, another
    tenant's, one whose secret is wrong and one that was never registered are
    one answer, so a browser holding an id it should not have learns nothing
    from the difference. The same rule `ReceiveInbound` follows.
    """
    if not device.proves_itself(secret):
        raise NotFound(f"device {asked_for} was not found")


def _mint() -> str:
    """A trigger's ``inbound_token`` is minted the same way, at the same width."""
    return secrets.token_urlsafe(32)


class RegisterDevice:
    """Idempotent on (tenant, principal, label).

    A reinstalled extension registers again, and must come back as the device it
    was rather than as a second one -- an administrator reading the device list
    is answering "whose browsers are being observed", and one operator appearing
    four times is not an answer.
    """

    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids

    async def execute(
        self, ctx: RequestContext, *, label: str, extension_version: str
    ) -> Registered:
        now = self._clock.now()
        async with self._uow as uow:
            policy = await current_policy(uow, ctx)
            known = await uow.devices.registered_as(ctx.tenant_id, ctx.principal_id, label)
            if known is not None:
                known.extension_version = extension_version
                # A device registered before secrets existed adopts one here.
                # This is the whole of the migration: the browser is refused on
                # its next device-scoped call, re-registers under the label it
                # always used, and comes back as itself holding a secret.
                secret = known.secret or _mint()
                known.secret = secret
                known.seen(now)
                await uow.devices.save(known)
                await uow.commit()
                return Registered(device_id=known.id, policy=policy, secret=secret)

            minted = _mint()
            device = AgentDevice(
                id=self._ids.new_device_id(),
                tenant_id=ctx.tenant_id,
                principal_id=ctx.principal_id,
                label=label,
                extension_version=extension_version,
                registered_at=now,
                last_seen_at=now,
                secret=minted,
            )
            try:
                await uow.devices.add(device)
                await uow.commit()
            except Conflict:
                # Two registrations for the same (tenant, principal, label)
                # raced. Idempotent means the loser comes back as the winner,
                # not as a 409 an extension that only ever registers once has
                # no reason to expect or retry. The winner is a row another
                # registration just wrote, so it holds a secret; a row that
                # somehow does not is one this cannot answer for, and a
                # conflict is more honest than a secret nobody stored.
                won = await uow.devices.registered_as(ctx.tenant_id, ctx.principal_id, label)
                if won is None or won.secret is None:
                    raise
                return Registered(device_id=won.id, policy=policy, secret=won.secret)
        return Registered(device_id=device.id, policy=policy, secret=minted)


class RecordHeartbeat:
    """Sixty seconds of "still here", and the two numbers worth having.

    The backlog a device reports is the only warning that an operator's day of
    work is sitting in a browser that cannot reach us.
    """

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(
        self,
        ctx: RequestContext,
        *,
        device_id: DeviceId,
        secret: str,
        queued_events: int = 0,
        queued_bytes: int = 0,
        policy_version: int | None = None,
    ) -> Beat:
        now = self._clock.now()
        async with self._uow as uow:
            device = await uow.devices.get(ctx.tenant_id, device_id)
            refuse_unless_itself(device, secret, device_id)
            device.seen(now, queued_events=queued_events, queued_bytes=queued_bytes)
            await uow.devices.save(device)
            policy = await current_policy(uow, ctx)
            await uow.commit()

        behind = policy_version is None or policy_version != policy.version
        return Beat(
            policy_version=policy.version,
            policy=policy if behind else None,
            pause=device.paused,
        )


class ReadDevice:
    """One device, and only if it is this tenant's and proved it is itself.

    The ownership check every device-scoped path makes: a tenant credential
    proves who is asking, never which browser they may ask about, so it says
    which tenant and the device's own secret says which browser. Neither is
    dropped -- without the credential a leaked secret would reach across
    tenants, and without the secret a device id is a namespace rather than a
    credential.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, ctx: RequestContext, *, device_id: DeviceId, secret: str
    ) -> AgentDevice:
        async with self._uow as uow:
            device = await uow.devices.get(ctx.tenant_id, device_id)
        refuse_unless_itself(device, secret, device_id)
        return device


class ReadDevices:
    """Whose browsers are being observed. The screen behind the consent story."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext) -> tuple[AgentDevice, ...]:
        async with self._uow as uow:
            return await uow.devices.list_for_tenant(ctx.tenant_id)
