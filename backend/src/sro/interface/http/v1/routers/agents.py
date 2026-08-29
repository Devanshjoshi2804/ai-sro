"""Extensions announcing themselves, and saying they are still there."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, status

from sro.application.context import RequestContext
from sro.application.trigger.fire_trigger import blank_inputs
from sro.container import Container
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import DeviceId, TriggerId
from sro.domain.trigger.trigger import Trigger
from sro.interface.http.deps import ContainerDep, ContextDep, DeviceSecretDep
from sro.interface.http.schemas import (
    DeviceModel,
    FiredModel,
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
    """Idempotent on the label: a reinstalled extension comes back as itself.

    The one device-scoped-ish route with no device secret on it, because it is
    where a secret comes from and there is no device yet to have one. What
    stands in its place is the idempotency key: (tenant, principal, label). A
    colleague holding another tenant credential registering the same label gets
    their own device under their own principal, never this one -- so the answer
    only ever hands a secret to the operator whose device it is.
    """
    registered = await container.register_device().execute(
        ctx, label=body.label, extension_version=body.extension_version
    )
    return RegisteredDeviceResponse(
        device_id=registered.device_id.value,
        device_secret=registered.secret,
        policy=ObservationPolicyModel.of(registered.policy),
        policy_version=registered.policy.version,
    )


@router.post("/{device_id}/heartbeat")
async def heartbeat(
    device_id: str,
    body: HeartbeatRequest,
    container: ContainerDep,
    ctx: ContextDep,
    x_device_secret: DeviceSecretDep = "",
) -> HeartbeatResponse:
    """Still here, this much is queued, and this is the policy I hold.

    Also where a browser finds out it has been left behind. A device from
    before secrets is refused here first, once a minute, and the extension
    answers a refusal by registering again -- which is idempotent on its label,
    so it comes back as the same device holding a secret. That is the whole
    migration, and it costs one operator nothing and one heartbeat.
    """
    beat = await container.record_heartbeat().execute(
        ctx,
        device_id=DeviceId(device_id),
        secret=x_device_secret,
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
    device_id: str,
    container: ContainerDep,
    ctx: ContextDep,
    x_device_secret: DeviceSecretDep = "",
) -> list[TriggerModel]:
    """What this browser is watching its operator's mail for.

    Asked by the extension, because a watch is evaluated in the browser that
    already has the mailbox open and nowhere else: nothing about the mail is
    sent here, so the rule has to go there.

    The device is read first, which is the ownership check the command channel
    does for the same reason: a credential proves who is asking, never which
    browser they may ask about, so a device id that leaked would otherwise be
    somebody else's mail rules. That check is now the device's own secret and
    not only its tenant -- a colleague's extension holds a perfectly valid
    tenant credential. Scoped to the device after that -- one operator never
    sees another's, even inside the same tenant.
    """
    device = await container.read_device().execute(
        ctx, device_id=DeviceId(device_id), secret=x_device_secret
    )
    watches = await container.read_triggers().watches(ctx, device_id=device.id)
    return [TriggerModel.of(trigger) for trigger in watches]


@router.post("/{device_id}/watches/{trigger_id}/matched")
async def watch_matched(
    device_id: str,
    trigger_id: str,
    container: ContainerDep,
    ctx: ContextDep,
    values: Annotated[dict[str, str], Body()] = {},  # noqa: B006
    x_device_secret: DeviceSecretDep = "",
) -> WatchMatchModel:
    """This browser recognised a mail. Nothing runs.

    A match is an offer. The plan is explicit that at this stage the panel says
    what matched and the operator presses once, so what this answers with is
    the offer itself -- and the press is a separate act, at `/fire` below.
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
    the difference. `ReadDevice` runs first all the same, which it did not need
    to when tenant scoping was the whole check: the device id names a browser
    and the secret is what says the caller is that browser, so the device has
    to be read to have a secret to compare against.
    """
    watch = await _watch_of(
        container, ctx, device_id=device_id, trigger_id=trigger_id, secret=x_device_secret
    )
    running_with = watch.values_from(values)
    skill = await container.get_skill().execute(ctx, skill_id=watch.skill_id)
    version = skill.runnable
    return WatchMatchModel(
        trigger_id=watch.id.value,
        skill_id=watch.skill_id.value,
        values=running_with,
        # A skill with no runnable version is not a shortage of values, and
        # saying "nothing said shipment_id" about one would send somebody
        # looking in the mail for a value that was never the problem. The press
        # answers that one, with the trigger's own words.
        missing=[] if version is None else blank_inputs(version, running_with),
    )


@router.post("/{device_id}/watches/{trigger_id}/fire", status_code=status.HTTP_202_ACCEPTED)
async def watch_fire(
    device_id: str,
    trigger_id: str,
    container: ContainerDep,
    ctx: ContextDep,
    values: Annotated[dict[str, str], Body()] = {},  # noqa: B006
    x_device_secret: DeviceSecretDep = "",
) -> FiredModel:
    """The press. The operator saw the offer and said do it.

    A sibling of `/matched` rather than a flag on it: the endpoint above
    answers a question and starts nothing, which is the whole of what it
    promises, and a `confirmed=true` that quietly made it start runs would make
    that promise conditional on a parameter. Same path, same ownership check,
    one answer each.

    The body is the values again, because nothing was kept: the offer lives in
    the browser that found it, so the press carries what the mail said the same
    way the report did. `/v1/triggers/{id}/fire` is left alone -- it fires with
    a trigger's own values and a schedule has no message to widen it for.

    From here it is an ordinary fire. `FireTrigger` reads only the names this
    trigger declared, re-reads the skill, and skips rather than starting a run
    whose required inputs are empty -- the same `blank_inputs` the offer showed
    before the press.
    """
    watch = await _watch_of(
        container, ctx, device_id=device_id, trigger_id=trigger_id, secret=x_device_secret
    )
    fired = await container.fire_trigger().execute(watch.id, message=values)
    return FiredModel(
        trigger_id=fired.trigger_id.value,
        run_id=fired.run_id.value if fired.run_id else None,
        skipped=fired.skipped,
    )


async def _watch_of(
    container: Container, ctx: RequestContext, *, device_id: str, trigger_id: str, secret: str
) -> Trigger:
    """This browser proving it is itself, then: this tenant's, this device's,
    enabled, and a watch. Anything else is `NotFound`, so a wrong secret,
    another device's watch, another tenant's, and one that never existed are
    one answer."""
    device = await container.read_device().execute(
        ctx, device_id=DeviceId(device_id), secret=secret
    )
    watches = await container.read_triggers().watches(ctx, device_id=device.id)
    watch = next((trigger for trigger in watches if trigger.id == TriggerId(trigger_id)), None)
    if watch is None:
        raise NotFound("no such watch")
    return watch


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
