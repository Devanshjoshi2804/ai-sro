from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from urllib.parse import urlsplit

from sro.application.connection.refusals import RefusedCredentials
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
        self._refused: set[str] = set()
        self._kept: dict[str, str] = {}
        self._host = ""

    async def __call__(self, key: str) -> str | None:
        once = self._held.take(key, run_id=self._run_id) or self._kept.get(key)
        if once is not None:
            self._kept[key] = once
            if _mark(key, once) in self._refused:
                return None
            self._handed[key] = (_mark(key, once), False)
            return once
        if self._vault is None:
            return None
        try:
            if await RefusedCredentials(self._vault).standing(key) is not None:
                return None
            value = await self._vault.get(key)
        except VaultUnavailable:
            return None
        if value is None:
            return None
        mark = _mark(key, value)
        if mark in self._refused:
            return None
        self._handed[key] = (mark, True)
        return value

    def typed(self, value: str) -> None:
        for key, (mark, _) in self._handed.items():
            if mark == _mark(key, value):
                self._typed[key] = self._host
                self._signing = True

    def pressed(self) -> None:
        if self._typed:
            self._signing = True
        self._attempts.update(self._typed)
        self._typed.clear()

    def step_ended(self, held: bool) -> None:
        if held and not self._signing:
            self._attempts.clear()
            self._failed.clear()
        self._signing = False

    async def saw(self, url: str, *, signed_out: bool, credential_empty: bool) -> None:
        host = urlsplit(url).netloc.lower()
        if not host:
            return
        self._host = host
        if not (signed_out and credential_empty):
            return
        for key, form in list(self._attempts.items()):
            if host != form:
                continue
            del self._attempts[key]
            self._failed[key] = self._failed.get(key, 0) + 1
            if self._failed[key] >= LATCH_AT:
                await self._refuse(key)

    async def _refuse(self, key: str) -> None:
        mark, from_vault = self._handed[key]
        self._refused.add(mark)
        if not from_vault or self._vault is None:
            return
        try:
            await RefusedCredentials(self._vault).refuse(
                key,
                at=datetime.now(tz=UTC),
                reason=(
                    f"run {self._run_id} submitted this password {LATCH_AT} times and each "
                    f"time the sign-in form on {self._host} came back with its password box empty"
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
    return action == "click" or (action == "press" and payload.get("value") in (None, "", "Enter"))


def _mark(key: str, value: str) -> str:
    return hashlib.sha256(f"{key}\0{value}".encode()).hexdigest()
