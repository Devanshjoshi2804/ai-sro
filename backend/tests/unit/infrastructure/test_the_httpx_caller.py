from __future__ import annotations

import httpx
import pytest

from sro.application.ports.http import MalformedRequest, TargetUnreachable
from sro.infrastructure.http.httpx_caller import HttpxCaller


async def test_a_cookie_one_answer_set_is_never_sent_on_the_next_call() -> None:
    carried: list[str | None] = []

    def server(request: httpx.Request) -> httpx.Response:
        carried.append(request.headers.get("cookie"))
        return httpx.Response(200, headers={"set-cookie": "sid=account-a; Path=/"})

    caller = HttpxCaller(transport=httpx.MockTransport(server))

    await caller.send("GET", "https://wms.example/a", headers={"cookie": "sid=account-a"})
    await caller.send("GET", "https://wms.example/b", headers={})

    assert carried == ["sid=account-a", None]


async def test_an_answer_that_cannot_be_decoded_arrived_and_is_not_a_malformed_request() -> None:
    arrived: list[str] = []

    def server(request: httpx.Request) -> httpx.Response:
        arrived.append(request.method)
        return httpx.Response(201, headers={"content-encoding": "gzip"}, content=b"not gzip")

    caller = HttpxCaller(transport=httpx.MockTransport(server))

    with pytest.raises(TargetUnreachable) as raised:
        await caller.send("POST", "https://wms.example/api/customer-types", headers={}, body="{}")

    assert not isinstance(raised.value, MalformedRequest)
    assert arrived == ["POST"]
