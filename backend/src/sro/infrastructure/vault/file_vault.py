"""Encrypted file vault.

The development and single-node deployment story, behind the same port a real
secret manager will use. Two properties it does not compromise on:

- **No key, no vault.** Without ``SRO_VAULT_KEY`` it refuses to start rather than
  writing plaintext. A store that silently degrades is worse than one that
  stops, because nothing downstream can tell.
- **The file is unreadable without the key**, so a backup, a stray copy or a
  laptop does not leak the customer's WMS login.

Swapping this for Vault or a cloud secret manager is one adapter.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from sro.application.ports.vault import VaultUnavailable


class FileCredentialVault:
    def __init__(self, *, path: Path, key: str | None) -> None:
        if not key:
            raise VaultUnavailable(
                "SRO_VAULT_KEY is not set. Generate one with `make vault-key` and put it in "
                "the environment; secrets are never written unencrypted."
            )
        try:
            self._fernet = Fernet(key.encode())
        except (ValueError, TypeError) as exc:
            raise VaultUnavailable(f"SRO_VAULT_KEY is not a valid Fernet key: {exc}") from exc

        self._path = path
        self._lock = asyncio.Lock()

    async def store(self, key: str, value: str) -> None:
        async with self._lock:
            secrets = self._read()
            secrets[key] = value
            self._write(secrets)

    async def get(self, key: str) -> str | None:
        async with self._lock:
            return self._read().get(key)

    async def delete(self, key: str) -> None:
        async with self._lock:
            secrets = self._read()
            if secrets.pop(key, None) is not None:
                self._write(secrets)

    def _read(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            decrypted = self._fernet.decrypt(self._path.read_bytes())
        except InvalidToken as exc:
            raise VaultUnavailable(
                f"{self._path} cannot be decrypted with this SRO_VAULT_KEY. The key changed, "
                "or the file belongs to another deployment."
            ) from exc
        loaded: dict[str, str] = json.loads(decrypted)
        return loaded

    def _write(self, secrets: dict[str, str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._fernet.encrypt(json.dumps(secrets).encode())
        # Written via a temp file in the same directory so a crash mid-write
        # cannot leave a half-file that decrypts to nothing.
        temporary = self._path.with_suffix(".tmp")
        temporary.write_bytes(payload)
        temporary.chmod(0o600)
        temporary.replace(self._path)
