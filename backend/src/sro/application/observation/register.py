"""An extension announcing itself, and saying it is still there."""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.observation.policy import current_policy
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.identifiers import DeviceId


@dataclass(frozen=True, slots=True)
class Registered:
    device_id: DeviceId
    policy: ObservationPolicy


@dataclass(frozen=True, slots=True)
class Beat:
    policy_version: int
    policy: ObservationPolicy | None
    """Only when the version the device holds is behind. A heartbeat that
    re-sent the whole policy every minute would be the largest thing this
    system says to a browser, and it says it once."""

    pause: bool


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
                known.seen(now)
                await uow.devices.save(known)
                await uow.commit()
                return Registered(device_id=known.id, policy=policy)

            device = AgentDevice(
                id=self._ids.new_device_id(),
                tenant_id=ctx.tenant_id,
                principal_id=ctx.principal_id,
                label=label,
                extension_version=extension_version,
                registered_at=now,
                last_seen_at=now,
            )
            await uow.devices.add(device)
            await uow.commit()
        return Registered(device_id=device.id, policy=policy)


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
        queued_events: int = 0,
        queued_bytes: int = 0,
        policy_version: int | None = None,
    ) -> Beat:
        now = self._clock.now()
        async with self._uow as uow:
            device = await uow.devices.get(ctx.tenant_id, device_id)
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
    """One device, and only if it is this tenant's.

    The command channel's ownership check: a credential proves who is asking,
    never what they may address, and a device id that leaked is otherwise a
    browser somebody else can be handed work in.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, device_id: DeviceId) -> AgentDevice:
        async with self._uow as uow:
            return await uow.devices.get(ctx.tenant_id, device_id)


class ReadDevices:
    """Whose browsers are being observed. The screen behind the consent story."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext) -> tuple[AgentDevice, ...]:
        async with self._uow as uow:
            return await uow.devices.list_for_tenant(ctx.tenant_id)
