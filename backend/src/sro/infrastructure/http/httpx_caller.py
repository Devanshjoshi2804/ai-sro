"""HttpCaller over httpx."""

from __future__ import annotations

from collections.abc import Mapping

import httpx

from sro.application.ports.http import HttpResponse, TargetUnreachable


class HttpxCaller:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        # No cookie jar and no redirect following: a session the executor was
        # not handed is a session it must not acquire, and a 302 on a mutation
        # is a fact the run should record rather than chase.
        self._client = client or httpx.AsyncClient(follow_redirects=False, cookies=None)

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
        except httpx.HTTPError as error:
            # httpx raises several of these with an empty message -- a read
            # error carries nothing but its class -- and a run that failed with
            # a blank reason costs an afternoon to attribute. The class name is
            # not much, and it is the difference between "unreachable" and
            # "nothing happened".
            raise TargetUnreachable(str(error) or type(error).__name__) from error

        return HttpResponse(
            status_code=response.status_code,
            headers={k.lower(): v for k, v in response.headers.items()},
            text=response.text,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
