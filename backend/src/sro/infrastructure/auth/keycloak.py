"""Offline tokens from Keycloak, so a run does not depend on a browser session.

The realm advertises what it will do -- `password`, `refresh_token` and the
`offline_access` scope -- and the WMS behind it distinguishes a bad token from
no credential at all: it answers a bearer it dislikes with 401 and a request
with nothing at all with a redirect to the identity provider. That difference
is what makes this worth building; an API that only understood cookies could
not be given a token however good the token was.

Two things are stored and they are not the same. The offline token is the thing
worth protecting: it acts as the operator until somebody revokes it, so it
lives in the vault and is never returned by anything. The access token it
produces is short-lived and kept in memory only, refreshed when it is close
enough to expiry that a slow call would outlive it.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from sro.application.ports.token import TokenRefused
from sro.application.ports.vault import CredentialVault

logger = logging.getLogger(__name__)

_EARLY = 60.0
"""Seconds before expiry to refresh anyway. A token that dies mid-call fails a
run for a reason that has nothing to do with the task."""


@dataclass(frozen=True, slots=True)
class _Live:
    token: str
    expires_at: float


class KeycloakTokens:
    def __init__(
        self,
        vault: CredentialVault,
        *,
        realm_url: str,
        client_id: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._vault = vault
        self._realm = realm_url.rstrip("/")
        self._client_id = client_id
        self._http = client or httpx.AsyncClient(timeout=30.0)
        self._live: dict[str, _Live] = {}

    def _key(self, tenant: str, system: str) -> str:
        """Tenant-scoped, like every other credential: one tenant's token must
        never authenticate another tenant's run."""
        return f"{tenant}/{system}/offline_token"

    async def establish(self, *, tenant: str, system: str, username: str, password: str) -> str:
        """One login, exchanged for something that outlives it."""
        answer = await self._grant(
            {
                "grant_type": "password",
                "client_id": self._client_id,
                "username": username,
                "password": password,
                # Without this the refresh token dies with the SSO session,
                # which is the whole problem being solved.
                "scope": "openid offline_access",
            }
        )
        offline = answer.get("refresh_token")
        if not offline:
            raise TokenRefused(
                "the identity provider issued no refresh token; this client may not be "
                "allowed to hold one"
            )
        await self._vault.store(self._key(tenant, system), str(offline))
        self._remember(tenant, system, answer)
        return system

    async def access_token(self, *, tenant: str, system: str) -> str | None:
        live = self._live.get(f"{tenant}/{system}")
        if live and live.expires_at - _EARLY > time.monotonic():
            return live.token

        offline = await self._vault.get(self._key(tenant, system))
        if not offline:
            return None

        answer = await self._grant(
            {
                "grant_type": "refresh_token",
                "client_id": self._client_id,
                "refresh_token": offline,
            }
        )
        # Rotation is on in some realms: the refresh that comes back replaces
        # the one that produced it, and keeping the old one means the next
        # refresh fails for a reason nobody would guess at.
        if rotated := answer.get("refresh_token"):
            await self._vault.store(self._key(tenant, system), str(rotated))
        return self._remember(tenant, system, answer)

    async def has_token(self, *, tenant: str, system: str) -> bool:
        return bool(await self._vault.get(self._key(tenant, system)))

    def _remember(self, tenant: str, system: str, answer: dict[str, object]) -> str:
        token = str(answer.get("access_token", ""))
        lifetime = float(answer.get("expires_in", 300) or 300)  # type: ignore[arg-type]
        self._live[f"{tenant}/{system}"] = _Live(
            token=token, expires_at=time.monotonic() + lifetime
        )
        return token

    async def _grant(self, form: dict[str, str]) -> dict[str, object]:
        try:
            response = await self._http.post(
                f"{self._realm}/protocol/openid-connect/token", data=form
            )
        except httpx.HTTPError as error:
            raise TokenRefused(f"could not reach the identity provider: {error}") from error

        if response.status_code != httpx.codes.OK:
            # The provider's own words, which name the actual problem --
            # invalid_grant for a revoked token, unauthorized_client for a
            # client that may not do this.
            detail = response.json().get("error_description") if _json(response) else response.text
            raise TokenRefused(f"the identity provider refused: {detail}"[:300])
        answer: dict[str, object] = response.json()
        return answer


def _json(response: httpx.Response) -> bool:
    return str(response.headers.get("content-type", "")).startswith("application/json")
