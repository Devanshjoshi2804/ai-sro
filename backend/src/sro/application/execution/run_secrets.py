from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sro.application.connection.refusals import RefusedCredentials
from sro.application.execution.one_time_secrets import OneTimeSecrets
from sro.application.ports.vault import CredentialVault, VaultUnavailable


class RunSecrets:
    def __init__(self, vault: CredentialVault | None, held: OneTimeSecrets, *, run_id: str) -> None:
        self._vault = vault
        self._held = held
        self._run_id = run_id
        self._handed: dict[str, str] = {}
        self._typed: set[str] = set()

    async def __call__(self, key: str) -> str | None:
        once = self._held.take(key, run_id=self._run_id)
        if once is not None:
            self._handed.pop(key, None)
            return once
        if self._vault is None:
            return None
        refusals = RefusedCredentials(self._vault)
        try:
            if await refusals.standing(key) is not None:
                return None
            value = await self._vault.get(key)
            if value is None:
                return None
            mark = _mark(key, value)
            if mark in self._typed:
                await refusals.refuse(
                    key,
                    at=datetime.now(tz=UTC),
                    reason=(
                        f"run {self._run_id} typed this password and was asked for it again: "
                        "the sign-in form came back, so it was not typed a second time"
                    ),
                )
                return None
        except VaultUnavailable:
            return None
        self._handed[key] = mark
        return value

    def typed(self, value: str) -> None:
        for key, mark in self._handed.items():
            if mark == _mark(key, value):
                self._typed.add(mark)


def _mark(key: str, value: str) -> str:
    return hashlib.sha256(f"{key}\0{value}".encode()).hexdigest()
