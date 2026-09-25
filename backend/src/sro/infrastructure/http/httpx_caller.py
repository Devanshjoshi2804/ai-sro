from __future__ import annotations

from collections.abc import Mapping
from http.cookiejar import CookieJar, DefaultCookiePolicy

import httpx

from sro.application.ports.http import HttpResponse, MalformedRequest, TargetUnreachable


class HttpxCaller:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._client = httpx.AsyncClient(
            follow_redirects=False,
            cookies=CookieJar(DefaultCookiePolicy(allowed_domains=[])),
            transport=transport,
        )

    async def send(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: str | None = None,
        timeout_s: float = 30.0,
    ) -> HttpResponse:
        try:
            response = await self._client.request(
                method.upper(),
                url,
                headers=dict(headers),
                content=body.encode() if body is not None else None,
                timeout=timeout_s,
            )
        except (
            httpx.InvalidURL,
            httpx.UnsupportedProtocol,
            httpx.LocalProtocolError,
        ) as wrong:
            raise MalformedRequest(str(wrong) or type(wrong).__name__) from wrong
        except httpx.HTTPError as error:
            raise TargetUnreachable(str(error) or type(error).__name__) from error

        return HttpResponse(
            status_code=response.status_code,
            headers={k.lower(): v for k, v in response.headers.items()},
            text=response.text,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
