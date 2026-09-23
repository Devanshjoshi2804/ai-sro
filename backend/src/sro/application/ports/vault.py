from __future__ import annotations

from typing import Protocol


class CredentialVault(Protocol):
    async def store(self, key: str, value: str) -> None: ...

    async def get(self, key: str) -> str | None: ...

    async def delete(self, key: str) -> None: ...


class VaultUnavailable(Exception):
    code = "no_vault"
