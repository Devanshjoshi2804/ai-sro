from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from urllib.parse import urlsplit

from sro.application.connection.refusals import FailedAttempts, RefusedCredentials, fingerprint
from sro.application.execution.one_time_secrets import OneTimeSecrets
from sro.application.ports.channel import Channel, Reply
from sro.application.ports.vault import CredentialVault, VaultUnavailable
from sro.domain.shared.identifiers import DeviceId, TenantId

TYPES = ("ui.perform", "ui.perform_at")
LATCH_AT = 2


class RunSecrets:
    def __init__(self, vault: CredentialVault | None, held: OneTimeSecrets, *, run_id: str) -> None:
        self._vault = vault
        self._held = held
        self._run_id = run_id
        self._handed: dict[str, tuple[str, bool]] = {}
        self._typed: dict[str, str] = {}
        self._attempts: dict[str, str] = {}
        self._failed: dict[str, int] = {}
        self._signing = False
        self._counted: set[str] = set()
        self._homes: dict[str, set[str]] = {}
        self._left: set[str] = set()
        self._refused: set[str] = set()
        self._kept: dict[str, str] = {}
        self._host = ""

    async def __call__(self, key: str) -> str | None:
        once = self._held.take(key, run_id=self._run_id) or self._kept.get(key)
        if once is not None:
            self._kept[key] = once
            if fingerprint(key, once) in self._refused:
                return None
            self._handed[key] = (fingerprint(key, once), False)
            return once
        if self._vault is None:
            return None
        try:
            value = await self._vault.get(key)
            if value is None:
                return None
            if await RefusedCredentials(self._vault).standing(key, value) is not None:
                return None
        except VaultUnavailable:
            return None
        mark = fingerprint(key, value)
        if mark in self._refused:
            return None
        self._handed[key] = (mark, True)
        return value

    def typed(self, value: str) -> None:
        for key, (mark, _) in self._handed.items():
            if mark == fingerprint(key, value):
                self._typed[key] = self._host
                self._signing = True

    def pressed(self) -> None:
        if self._typed:
            self._signing = True
        for key, host in self._typed.items():
            self._homes.setdefault(key, set()).add(host)
            self._left.discard(key)
            if self._handed[key][1]:
                self._counted.add(key)
        self._attempts.update(self._typed)
        self._typed.clear()

    async def step_ended(self, held: bool, origin: str | None = None) -> None:
        signing, self._signing = self._signing, False
        if not held or signing:
            return
        here = urlsplit(origin).netloc.lower() if origin else self._host
        mine = [key for key, hosts in self._homes.items() if here in hosts]
        for key in mine:
            self._attempts.pop(key, None)
            self._failed.pop(key, None)
        await self._forget(mine)

    async def finished(self) -> None:
        await self._forget(list(self._left))

    async def _forget(self, keys: list[str]) -> None:
        if self._vault is None:
            return
        for key in keys:
            if key not in self._counted:
                continue
            try:
                await FailedAttempts(self._vault).clear(key)
            except VaultUnavailable:
                continue
            self._counted.discard(key)

    async def saw(self, url: str, *, signed_out: bool, credential_empty: bool) -> None:
        host = urlsplit(url).netloc.lower()
        if not host:
            return
        self._host = host
        for key, form in self._attempts.items():
            if not signed_out and host != form and key not in self._left:
                self._left.add(key)
                self._homes[key].add(host)
        if not (signed_out and credential_empty):
            return
        for key, form in list(self._attempts.items()):
            if host != form:
                continue
            del self._attempts[key]
            self._left.discard(key)
            self._failed[key] = self._failed.get(key, 0) + 1
            if await self._count(key) >= LATCH_AT:
                await self._refuse(key)

    async def _count(self, key: str) -> int:
        mark, from_vault = self._handed[key]
        if not from_vault or self._vault is None:
            return self._failed[key]
        try:
            return await FailedAttempts(self._vault).add(key, mark)
        except VaultUnavailable:
            return self._failed[key]

    async def _refuse(self, key: str) -> None:
        mark, from_vault = self._handed[key]
        self._refused.add(mark)
        if not from_vault or self._vault is None:
            return
        try:
            await RefusedCredentials(self._vault).refuse(
                key,
                at=datetime.now(tz=UTC),
                fingerprint=mark,
                reason=(
                    f"this password was submitted {LATCH_AT} times with no success between, the "
                    f"last by run {self._run_id}, and each time the sign-in form on {self._host} "
                    "came back with its password box empty"
                ),
            )
        except VaultUnavailable:
            return


class WatchingChannel:
    def __init__(self, channel: Channel, secrets: RunSecrets) -> None:
        self._channel = channel
        self._secrets = secrets

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
        reply = await self._channel.send(
            tenant_id, device_id, kind=kind, payload=payload, run_id=run_id, deadline_s=deadline_s
        )
        if not reply.ok:
            return reply
        if kind == "ui.url":
            ours = reply.result.get("elsewhere") if reply.result.get("elsewhere_is_ours") else ""
            await self._secrets.saw(
                str(reply.result.get("url") or ours or ""),
                signed_out=bool(reply.result.get("signed_out")),
                credential_empty=bool(reply.result.get("credential_empty")),
            )
        typed = payload.get("value") if kind in TYPES else payload.get("password")
        if kind in (*TYPES, "sign_in") and isinstance(typed, str):
            self._secrets.typed(typed)
        if kind == "sign_in" or (kind in TYPES and _submits(payload)):
            self._secrets.pressed()
        return reply

    def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]:
        return self._channel.online(tenant_id)

    def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        return self._channel.drop(tenant_id, device_id)


def _submits(payload: Mapping[str, object]) -> bool:
    action = payload.get("action")
    return action == "click" or (
        action == "press" and payload.get("value") in (None, "", "Enter", "NumpadEnter")
    )
