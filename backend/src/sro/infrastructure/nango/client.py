from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import datetime

import httpx

from sro.application.ports.nango import NangoConnection, NangoUnavailable

logger = logging.getLogger(__name__)

DOWN = "Connections are unavailable right now; try again shortly"
MISCONFIGURED = "Connections are misconfigured on this server"

K_PAGE_SIZE = 100
# ponytail: one end user rarely holds more than a few connections; stop after this many pages.
K_MAX_PAGES = 10


class NangoClient:
    def __init__(
        self,
        url: str,
        secret_key: str,
        http: httpx.AsyncClient | None = None,
        page_size: int = K_PAGE_SIZE,
    ) -> None:
        self._page_size = page_size
        self._http = http or httpx.AsyncClient(timeout=15.0)
        self._base = url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {secret_key}"}

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _send(
        self,
        method: str,
        path: str,
        *,
        extra: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        json: object | None = None,
    ) -> httpx.Response:
        try:
            return await self._http.request(
                method,
                f"{self._base}{path}",
                headers={**self._headers, **(extra or {})},
                params=params,
                json=json,
            )
        except httpx.HTTPError:
            logger.warning("nango %s %s unreachable", method, path)
            raise NangoUnavailable(DOWN) from None

    async def _ok(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        json: object | None = None,
    ) -> httpx.Response:
        response = await self._send(method, path, params=params, json=json)
        if response.is_error:
            logger.warning("nango %s %s answered %s", method, path, response.status_code)
            if response.status_code in (401, 403):
                raise NangoUnavailable(MISCONFIGURED)
            raise NangoUnavailable(DOWN)
        return response

    async def create_connect_session(
        self, end_user_id: str, display_name: str, organization_id: str, integrations: Sequence[str]
    ) -> str:
        response = await self._ok(
            "POST",
            "/connect/sessions",
            json={
                "tags": {
                    "end_user_id": end_user_id,
                    "end_user_display_name": display_name,
                    "organization_id": organization_id,
                },
                "allowed_integrations": list(integrations),
            },
        )
        try:
            return str(response.json()["data"]["token"])
        except (ValueError, KeyError, TypeError):
            logger.warning("nango POST /connect/sessions answered a body we cannot read")
            raise NangoUnavailable(DOWN) from None

    async def connections(self, end_user_id: str) -> list[NangoConnection]:
        found: list[NangoConnection] = []
        for page in range(K_MAX_PAGES):
            response = await self._ok(
                "GET",
                "/connection",
                params={
                    "tags[end_user_id]": end_user_id,
                    "limit": str(self._page_size),
                    "page": str(page),
                },
            )
            try:
                rows = response.json()["connections"]
                found += [
                    NangoConnection(
                        one["connection_id"],
                        one["provider_config_key"],
                        datetime.fromisoformat(one["created"]),
                        healthy=not one.get("errors"),
                    )
                    for one in rows
                ]
            except (ValueError, KeyError, TypeError):
                logger.warning("nango GET /connection answered a body we cannot read")
                raise NangoUnavailable(DOWN) from None
            if len(rows) < self._page_size:
                break
        return found

    async def proxy(
        self,
        method: str,
        path: str,
        *,
        connection_id: str,
        integration: str,
        params: Mapping[str, str] | None = None,
        body: object | None = None,
    ) -> httpx.Response:
        return await self._send(
            method.upper(),
            f"/proxy{path}",
            extra={"Connection-Id": connection_id, "Provider-Config-Key": integration},
            params=params,
            json=body,
        )
