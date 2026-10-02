from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sro.application.ports.vault import CredentialVault

MARK = "#refused"
FAILED = "#failed"
CODE = "#code"
MARKS = (MARK, FAILED)
FINGERPRINT = 12


def fingerprint(key: str, value: str) -> str:
    return hashlib.sha256(f"{key}\0{value}".encode()).hexdigest()[:FINGERPRINT]


@dataclass(frozen=True, slots=True)
class Refusal:
    at: datetime | None
    reason: str
    fingerprint: str = ""


class RefusedCredentials:
    def __init__(self, vault: CredentialVault) -> None:
        self._vault = vault

    async def refuse(self, key: str, *, at: datetime, reason: str, fingerprint: str = "") -> None:
        said = {"at": at.isoformat(), "reason": reason, "fingerprint": fingerprint}
        await self._vault.store(key + MARK, json.dumps(said))

    async def standing(self, key: str, value: str | None = None) -> Refusal | None:
        said = await self._vault.get(key + MARK)
        if not said:
            return None
        try:
            body = json.loads(said)
            refusal = Refusal(
                at=datetime.fromisoformat(body["at"]),
                reason=str(body["reason"]),
                fingerprint=str(body.get("fingerprint") or ""),
            )
        except (ValueError, KeyError, TypeError, AttributeError):
            return Refusal(at=None, reason=said)
        stale = value is not None and refusal.fingerprint not in ("", fingerprint(key, value))
        return None if stale else refusal


class CodeAsked:
    def __init__(self, vault: CredentialVault) -> None:
        self._vault = vault

    async def ask(self, key: str, *, at: datetime) -> None:
        await self._vault.store(key + CODE, json.dumps({"at": at.isoformat()}))

    async def since(self, key: str) -> datetime | None:
        said = await self._vault.get(key + CODE)
        if not said:
            return None
        try:
            return datetime.fromisoformat(json.loads(said)["at"])
        except (ValueError, KeyError, TypeError):
            return None

    async def clear(self, key: str) -> None:
        await self._vault.delete(key + CODE)


class FailedAttempts:
    def __init__(self, vault: CredentialVault) -> None:
        self._vault = vault

    async def add(self, key: str, fingerprint: str) -> int:
        count, _, against = (await self._vault.get(key + FAILED) or "").partition(" ")
        counted = int(count) if count.isdigit() and against == fingerprint else 0
        await self._vault.store(key + FAILED, f"{counted + 1} {fingerprint}")
        return counted + 1

    async def clear(self, key: str) -> None:
        await self._vault.delete(key + FAILED)


class ForgetsRefusalOnWrite:
    def __init__(
        self, vault: CredentialVault, *, on_written: Callable[[str], None] = lambda key: None
    ) -> None:
        self._vault, self._on_written = vault, on_written

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
        self._on_written(key)
        for mark in MARKS:
            await self._vault.delete(key + mark)
