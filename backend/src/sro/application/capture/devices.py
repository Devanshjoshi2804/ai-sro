from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.agent import AgentDrivers
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.observation.device import AgentDevice
from sro.domain.shared.identifiers import DeviceId


class RevokeDevice:
    def __init__(self, uow: UnitOfWork, drivers: AgentDrivers, clock: Clock) -> None:
        self._uow = uow
        self._drivers = drivers
        self._clock = clock

    async def execute(self, ctx: RequestContext, *, device_id: DeviceId) -> bool:
        now = self._clock.now()
        async with self._uow as uow:
            revoked = await uow.devices.revoke(ctx.tenant_id, device_id, at=now.isoformat())
            await uow.commit()
        self._drivers.drop(ctx.tenant_id, device_id)
        return revoked


class RestoreDevice:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, device_id: DeviceId) -> bool:
        async with self._uow as uow:
            restored = await uow.devices.restore(ctx.tenant_id, device_id)
            await uow.commit()
        return restored


@dataclass(frozen=True, slots=True)
class DeviceLine:
    device: AgentDevice
    online: bool


class ReadRoster:
    def __init__(self, uow: UnitOfWork, drivers: AgentDrivers) -> None:
        self._uow = uow
        self._drivers = drivers

    async def execute(self, ctx: RequestContext) -> tuple[DeviceLine, ...]:
        async with self._uow as uow:
            devices = await uow.devices.list_for_tenant(ctx.tenant_id)
        connected = frozenset(await self._drivers.online(ctx.tenant_id))
        return tuple(
            DeviceLine(device=device, online=device.id in connected and not device.revoked)
            for device in devices
        )
