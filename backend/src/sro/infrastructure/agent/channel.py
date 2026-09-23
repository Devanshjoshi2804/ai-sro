from __future__ import annotations

from collections.abc import Mapping

from sro.application.ports.channel import Channel, Reply
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.infrastructure.agent.sockets import DeviceSockets


class SocketChannel(Channel):
    def __init__(self, sockets: DeviceSockets) -> None:
        self._sockets = sockets

    async def send(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply:
        if deadline_s is not None and deadline_s <= 0:
            return Reply(ok=False, error_kind="timeout", error_detail="a non-positive deadline")
        answer = await self._sockets.send(
            tenant_id,
            device_id,
            kind=kind,
            payload=payload,
            run_id=run_id,
            timeout_s=deadline_s,
            source="rig",
        )
        return Reply(
            ok=answer.ok,
            result=answer.result,
            error_kind=answer.error_kind,
            error_detail=answer.error_detail,
        )

    def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]:
        return self._sockets.online(tenant_id)

    def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        return self._sockets.drop(tenant_id, device_id)
