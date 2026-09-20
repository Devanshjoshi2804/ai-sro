"""An extension announcing itself, and saying it is still there."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlsplit

from sro.application.context import RequestContext
from sro.application.observation.policy import current_policy
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.grant import LONGEST
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.errors import Conflict, NotFound
from sro.domain.shared.identifiers import DeviceId
from sro.infrastructure.telemetry.whose import attribute


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
    tenant's, one whose secret is wrong, one that was revoked and one that was
    never registered are one answer, so a browser holding an id it should not
    have learns nothing from the difference. The same rule `ReceiveInbound`
    follows.

    A revoked browser is refused before its secret is even compared. Revoking
    leaves the secret alone -- it has to, because a device with no secret cannot
    be told from one registered before secrets existed -- so a gate that asked
    only "is this the browser that registered" would answer yes forever, and
    the extension would resume on its next heartbeat. This is the one place
    that turns `revoked_at` into a refusal, for all seven device-scoped callers
    at once. The rig's `holder` did it in its `WHERE revoked_at IS NULL`.
    """
    if device.revoked or not device.proves_itself(secret):
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
        # After it has proved itself, never before -- `asking_device`'s rule,
        # and this is the other half of the same check. Here rather than at the
        # six routes that make it: the device id is in the path on every
        # `/v1/agents/{device_id}/...` route and was on none of their log
        # lines, and one attribution where they all go through is smaller than
        # six that the seventh will forget.
        attribute(device=device.id.value)
        return device


class GrantHost:
    """The operator saying this page may be watched after all.

    Behind the device's own secret like every device-scoped path: the tenant
    credential says who is asking and can never say which browser, and the
    whole justification for a grant is that the person whose browser it is
    chose it. A grant somebody else could add for you is not consent.
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
        host: str,
        lasting: timedelta = LONGEST,
    ) -> AgentDevice:
        now = self._clock.now()
        async with self._uow as uow:
            device = await uow.devices.get(ctx.tenant_id, device_id)
            refuse_unless_itself(device, secret, device_id)
            if device.principal_id != ctx.principal_id:
                # The device proved it is itself, so this is that browser --
                # but a browser is not a person, and the panel's button is
                # only consent when the person pressing it is the one being
                # observed. Refused as not-found for the same reason as
                # everything else on this path.
                raise NotFound(f"device {device_id} was not found")
            device.grant(
                _hostname(host),
                by=ctx.principal_id,
                at=now,
                until=now + min(lasting, LONGEST),
            )
            await uow.devices.save(device)
            await uow.commit()
        return device


class RevokeHost:
    """Stop watching it. The operator closing the tab, or pressing the button.

    Revoking something never granted is success: a tab closing twice, a browser
    catching up after being offline, and a grant that expired on its own all
    end in the same place, and none of them is an error worth showing anybody.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, ctx: RequestContext, *, device_id: DeviceId, secret: str, host: str
    ) -> AgentDevice:
        async with self._uow as uow:
            device = await uow.devices.get(ctx.tenant_id, device_id)
            refuse_unless_itself(device, secret, device_id)
            device.revoke(_hostname(host))
            await uow.devices.save(device)
            await uow.commit()
        return device


def _hostname(raw: str) -> str:
    """The host a grant is for, as `ObservationPolicy.allows` will compare it.

    A URL is accepted as well as a bare host because the panel has one and not
    the other, and a grant stored as `https://mail.google.com/mail/u/0` would
    match nothing while looking exactly like it should.
    """
    text = raw.strip()
    host = urlsplit(text).hostname if "//" in text else text
    return (host or "").strip().rstrip(".").lower()
