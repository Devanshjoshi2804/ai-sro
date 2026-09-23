from __future__ import annotations

import asyncio
import contextlib
import hashlib
import re
from typing import Protocol

from sro.application.ports.vault import VaultUnavailable

MAX_ID = 255

_ALLOWED = re.compile(r"[^A-Za-z0-9_-]")

_DIGEST = 12


def secret_id_for(key: str) -> str:
    readable = _ALLOWED.sub("-", key.replace("/", "_"))
    digest = hashlib.sha256(key.encode()).hexdigest()[:_DIGEST]
    room = MAX_ID - len(digest) - 2
    return f"{readable[:room]}__{digest}"


class _Secrets(Protocol):
    def create_secret(self, request: dict[str, object]) -> object: ...
    def add_secret_version(self, request: dict[str, object]) -> object: ...
    def access_secret_version(self, request: dict[str, object]) -> object: ...
    def delete_secret(self, request: dict[str, object]) -> object: ...


class SecretManagerVault:
    def __init__(self, *, project: str, client: _Secrets | None = None) -> None:
        if not project.strip():
            raise VaultUnavailable("SRO_VAULT_PROJECT is empty; name the Google project")
        self._project = project.strip()
        self._client = client or _real_client()

    def _name(self, key: str) -> str:
        return f"projects/{self._project}/secrets/{secret_id_for(key)}"

    async def store(self, key: str, value: str) -> None:
        await asyncio.to_thread(self._store, key, value)

    def _store(self, key: str, value: str) -> None:
        from google.api_core import exceptions

        try:
            with contextlib.suppress(exceptions.AlreadyExists):
                self._client.create_secret(
                    request={
                        "parent": f"projects/{self._project}",
                        "secret_id": secret_id_for(key),
                        "secret": {"replication": {"automatic": {}}},
                    }
                )
            self._client.add_secret_version(
                request={"parent": self._name(key), "payload": {"data": value.encode()}}
            )
        except exceptions.GoogleAPIError as refused:
            raise VaultUnavailable(f"the secret store refused a write: {refused}") from refused

    async def get(self, key: str) -> str | None:
        return await asyncio.to_thread(self._get, key)

    def _get(self, key: str) -> str | None:
        from google.api_core import exceptions

        try:
            answered = self._client.access_secret_version(
                request={"name": f"{self._name(key)}/versions/latest"}
            )
        except exceptions.NotFound:
            return None
        except exceptions.GoogleAPIError as refused:
            raise VaultUnavailable(f"the secret store could not be read: {refused}") from refused
        payload = getattr(answered, "payload", None)
        data = getattr(payload, "data", None)
        return None if data is None else bytes(data).decode()

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._delete, key)

    def _delete(self, key: str) -> None:
        from google.api_core import exceptions

        try:
            self._client.delete_secret(request={"name": self._name(key)})
        except exceptions.NotFound:
            return
        except exceptions.GoogleAPIError as refused:
            raise VaultUnavailable(f"the secret store refused a delete: {refused}") from refused


def _real_client() -> _Secrets:
    try:
        from google.cloud import secretmanager
    except ImportError as missing:
        raise VaultUnavailable(
            "SRO_VAULT_PROJECT names a Google project, but this deployment was installed "
            "without the client for it: install `.[gcp]`"
        ) from missing
    try:
        client: _Secrets = secretmanager.SecretManagerServiceClient()
    except Exception as unusable:
        raise VaultUnavailable(
            "SRO_VAULT_PROJECT names a Google project and its secret store could not be "
            f"opened: {unusable}"
        ) from unusable
    return client
