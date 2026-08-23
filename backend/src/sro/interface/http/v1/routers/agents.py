"""Extensions announcing themselves, and saying they are still there."""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.domain.shared.identifiers import DeviceId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    DeviceModel,
    HeartbeatRequest,
    HeartbeatResponse,
    ObservationPolicyModel,
    RegisterDeviceRequest,
    RegisteredDeviceResponse,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_device(
    body: RegisterDeviceRequest, container: ContainerDep, ctx: ContextDep
) -> RegisteredDeviceResponse:
    """Idempotent on the label: a reinstalled extension comes back as itself."""
    registered = await container.register_device().execute(
        ctx, label=body.label, extension_version=body.extension_version
    )
    return RegisteredDeviceResponse(
        device_id=registered.device_id.value,
        policy=ObservationPolicyModel.of(registered.policy),
        policy_version=registered.policy.version,
    )


@router.post("/{device_id}/heartbeat")
async def heartbeat(
    device_id: str, body: HeartbeatRequest, container: ContainerDep, ctx: ContextDep
) -> HeartbeatResponse:
    """Still here, this much is queued, and this is the policy I hold."""
    beat = await container.record_heartbeat().execute(
        ctx,
        device_id=DeviceId(device_id),
        queued_events=body.queued_events,
        queued_bytes=body.queued_bytes,
        policy_version=body.policy_version,
    )
    return HeartbeatResponse(
        policy_version=beat.policy_version,
        policy=None if beat.policy is None else ObservationPolicyModel.of(beat.policy),
        pause=beat.pause,
    )


@router.get("")
async def list_devices(container: ContainerDep, ctx: ContextDep) -> list[DeviceModel]:
    """Whose browsers are being observed. The screen behind the consent story."""
    devices = await container.read_devices().execute(ctx)
    return [DeviceModel.of(device) for device in devices]


@router.get("/policy")
async def read_policy(container: ContainerDep, ctx: ContextDep) -> ObservationPolicyModel:
    """Readable over HTTP, changeable only from a shell. There is no role model
    here, so an endpoint that switched observation on would let any operator
    consent on their colleagues' behalf."""
    return ObservationPolicyModel.of(await container.read_observation_policy().execute(ctx))
