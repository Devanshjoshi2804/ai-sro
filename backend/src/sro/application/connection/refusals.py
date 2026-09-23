from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sro.application.ports.vault import CredentialVault

MARK = "#refused"
FAILED = "#failed"
MARKS = (MARK, FAILED)


@dataclass(frozen=True, slots=True)
class Refusal:
    at: datetime | None
    reason: str


class RefusedCredentials:
    def __init__(self, vault: CredentialVault) -> None:
        self._vault = vault

    async def refuse(self, key: str, *, at: datetime, reason: str) -> None:
        await self._vault.store(key + MARK, json.dumps({"at": at.isoformat(), "reason": reason}))

    async def standing(self, key: str) -> Refusal | None:
        said = await self._vault.get(key + MARK)
        if not said:
            return None
        try:
            body = json.loads(said)
            return Refusal(at=datetime.fromisoformat(body["at"]), reason=str(body["reason"]))
        except (ValueError, KeyError, TypeError):
            return Refusal(at=None, reason=said)


class FailedAttempts:
    def __init__(self, vault: CredentialVault) -> None:
        self._vault = vault

    async def add(self, key: str) -> int:
        said = await self._vault.get(key + FAILED) or ""
        count = (int(said) if said.isdigit() else 0) + 1
        await self._vault.store(key + FAILED, str(count))
        return count

    async def clear(self, key: str) -> None:
        await self._vault.delete(key + FAILED)


class ForgetsRefusalOnWrite:
    def __init__(self, vault: CredentialVault) -> None:
        self._vault = vault

    async def store(self, key: str, value: str) -> None:
        await self._vault.store(key, value)
        await self._forget(key)

    async def get(self, key: str) -> str | None:
        return await self._vault.get(key)

    async def delete(self, key: str) -> None:
        await self._vault.delete(key)
        await self._forget(key)

    async def _forget(self, key: str) -> None:
        if key.endswith(MARKS):
            return
        for mark in MARKS:
            await self._vault.delete(key + mark)
