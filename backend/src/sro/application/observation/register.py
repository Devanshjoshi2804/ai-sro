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
from sro.whose import attribute


@dataclass(frozen=True, slots=True)
class Registered:
    device_id: DeviceId
    policy: ObservationPolicy
    secret: str


@dataclass(frozen=True, slots=True)
class Beat:
    policy_version: int
    policy: ObservationPolicy | None

    pause: bool


def refuse_unless_itself(device: AgentDevice, secret: str, asked_for: DeviceId) -> None:
    if device.revoked or not device.proves_itself(secret):
        raise NotFound(f"device {asked_for} was not found")
    attribute(device=device.id.value)


def _mint() -> str:
    return secrets.token_urlsafe(32)


class RegisterDevice:
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
                won = await uow.devices.registered_as(ctx.tenant_id, ctx.principal_id, label)
                if won is None or won.secret is None:
                    raise
                return Registered(device_id=won.id, policy=policy, secret=won.secret)
        return Registered(device_id=device.id, policy=policy, secret=minted)


class RecordHeartbeat:
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
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, ctx: RequestContext, *, device_id: DeviceId, secret: str
    ) -> AgentDevice:
        async with self._uow as uow:
            device = await uow.devices.get(ctx.tenant_id, device_id)
        refuse_unless_itself(device, secret, device_id)
        return device


class GrantHost:
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
    text = raw.strip()
    host = urlsplit(text).hostname if "//" in text else text
    return (host or "").strip().rstrip(".").lower()
