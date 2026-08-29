"""Extensions announcing themselves, and saying they are still there."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, status

from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import DeviceId, TriggerId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    DeviceModel,
    HeartbeatRequest,
    HeartbeatResponse,
    ObservationPolicyModel,
    RegisterDeviceRequest,
    RegisteredDeviceResponse,
    TriggerModel,
    WatchMatchModel,
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


@router.post("/{device_id}/watches/{trigger_id}/matched")
async def watch_matched(
    device_id: str,
    trigger_id: str,
    container: ContainerDep,
    ctx: ContextDep,
    values: Annotated[dict[str, str], Body()] = {},  # noqa: B006
) -> WatchMatchModel:
    """This browser recognised a mail. Nothing runs.

    A match is an offer. The plan is explicit that at this stage the panel says
    what matched and the operator presses once, so what this answers with is
    the offer itself -- and the press is a separate act, in a later slice.
    Nothing is written down either: the values were read out of somebody's mail
    and `ValueAt` exists to keep exactly those out of storage, so a table of
    pending matches would be the one thing the domain went structural lengths
    to prevent. The offer's home is the browser that found it.

    The body is only values. Not a subject, not a sender, not a screenshot, not
    a sentence about why -- there is nowhere in this signature to put one, which
    is a stronger guarantee than a rule someone has to remember. A name the
    watch never declared is dropped rather than refused, the same way an inbound
    relay adding a field to its payload is not a reason for a working rule to
    start failing.

    Which watch this device may report on is `ReadTriggers.watches` -- this
    tenant's, this device's, enabled, and a watch. Anything else is `NotFound`,
    so another device's watch, another tenant's, and one that never existed are
    one answer: a browser holding an id it should not have learns nothing from
    the difference. No `ReadDevice` first, unlike the endpoint above, which
    needs one because an empty list is otherwise the same answer for a browser
    with no rules and a browser in another tenant. Here the trigger read is
    already tenant-scoped, so that check could only produce the 404 this
    already produces.
    """
    watches = await container.read_triggers().watches(ctx, device_id=DeviceId(device_id))
    watch = next((trigger for trigger in watches if trigger.id == TriggerId(trigger_id)), None)
    if watch is None:
        raise NotFound("no such watch")
    return WatchMatchModel(
        trigger_id=watch.id.value,
        skill_id=watch.skill_id.value,
        values=watch.values_from(values),
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
