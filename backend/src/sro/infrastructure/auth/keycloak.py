from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from sro.application.ports.token import TokenRefused
from sro.application.ports.vault import CredentialVault

logger = logging.getLogger(__name__)

_EARLY = 60.0


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
        client_secret: str = "",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._vault = vault
        self._realm = realm_url.rstrip("/")
        self._client_id = client_id
        self._secret = client_secret
        self._http = client or httpx.AsyncClient(timeout=30.0)
        self._live: dict[str, _Live] = {}

    def _key(self, tenant: str, system: str) -> str:
        return f"{tenant}/{system}/offline_token"

    async def establish(self, *, tenant: str, system: str, username: str, password: str) -> str:
        answer = await self._grant(
            {
                "grant_type": "password",
                "client_id": self._client_id,
                "username": username,
                "password": password,
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
        if rotated := answer.get("refresh_token"):
            await self._vault.store(self._key(tenant, system), str(rotated))
        return self._remember(tenant, system, answer)

    def _remember(self, tenant: str, system: str, answer: dict[str, object]) -> str:
        token = str(answer.get("access_token", ""))
        lifetime = float(answer.get("expires_in", 300) or 300)  # type: ignore[arg-type]
        self._live[f"{tenant}/{system}"] = _Live(
            token=token, expires_at=time.monotonic() + lifetime
        )
        return token

    async def _grant(self, form: dict[str, str]) -> dict[str, object]:
        if self._secret:
            form = {**form, "client_secret": self._secret}
        try:
            response = await self._http.post(
                f"{self._realm}/protocol/openid-connect/token", data=form
            )
        except httpx.HTTPError as error:
            raise TokenRefused(f"could not reach the identity provider: {error}") from error

        if response.status_code != httpx.codes.OK:
            detail = response.json().get("error_description") if _json(response) else response.text
            raise TokenRefused(f"the identity provider refused: {detail}"[:300])
        answer: dict[str, object] = response.json()
        return answer


def _json(response: httpx.Response) -> bool:
    return str(response.headers.get("content-type", "")).startswith("application/json")
