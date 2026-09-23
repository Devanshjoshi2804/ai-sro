from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sro.application.ports.vault import CredentialVault

MARK = "#refused"


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


class ForgetsRefusalOnWrite:
    def __init__(self, vault: CredentialVault) -> None:
        self._vault = vault

    async def store(self, key: str, value: str) -> None:
        await self._vault.store(key, value)
        if not key.endswith(MARK):
            await self._vault.delete(key + MARK)

    async def get(self, key: str) -> str | None:
        return await self._vault.get(key)

    async def delete(self, key: str) -> None:
        await self._vault.delete(key)
        if not key.endswith(MARK):
            await self._vault.delete(key + MARK)
