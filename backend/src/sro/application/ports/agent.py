from __future__ import annotations

from typing import Protocol

from sro.application.ports.http import HttpCaller
from sro.application.ports.ui import UiDriver
from sro.domain.shared.identifiers import DeviceId, TenantId


class AgentDrivers(Protocol):
    def ui(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        origin: str | None = None,
        may_take_focus: bool = False,
        starts_on: str | None = None,
        doing: str = "",
        step: int | None = None,
        of: int | None = None,
    ) -> UiDriver: ...

    def http(self, tenant_id: TenantId, device_id: DeviceId) -> HttpCaller: ...

    async def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]: ...

    def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool: ...

    async def held_for(self, tenant_id: TenantId, device_id: DeviceId) -> float | None: ...


class DeviceUnreachable(Exception): ...
