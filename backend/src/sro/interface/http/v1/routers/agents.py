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
    TriggerModel,
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


@router.get("/{device_id}/watches")
async def list_watches(
    device_id: str, container: ContainerDep, ctx: ContextDep
) -> list[TriggerModel]:
    """What this browser is watching its operator's mail for.

    Asked by the extension, because a watch is evaluated in the browser that
    already has the mailbox open and nowhere else: nothing about the mail is
    sent here, so the rule has to go there.

    The device is read first, which is the ownership check the command channel
    does for the same reason: a credential proves who is asking, never which
    browser they may ask about, so a device id that leaked would otherwise be
    somebody else's mail rules. Scoped to the device after that -- one operator
    never sees another's, even inside the same tenant.
    """
    device = await container.read_device().execute(ctx, device_id=DeviceId(device_id))
    watches = await container.read_triggers().watches(ctx, device_id=device.id)
    return [TriggerModel.of(trigger) for trigger in watches]


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
