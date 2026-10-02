"""One-click connectors over the real stack: router, use case, NangoClient, and an httpx
MockTransport standing in for Nango.

Nango shapes verified against https://nango.dev/docs/reference/api/connect/sessions/create,
https://nango.dev/docs/reference/api/connection/list and
https://nango.dev/docs/reference/api/proxy/get.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable

import httpx
import pytest
from pydantic import SecretStr

from sro.config import Settings
from sro.infrastructure.nango.client import NangoClient
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

SECRET = "nango-secret-key-do-not-leak"  # noqa: S105
Handler = Callable[[httpx.Request], httpx.Response]


def _container(
    handler: Handler | None, integrations: tuple[str, ...] = ("microsoft",)
) -> _FakeContainer:
    container = _FakeContainer(FakeUnitOfWork())
    container.settings = Settings(
        nango_url="http://nango:8080",
        nango_secret_key=SecretStr(SECRET),
        integrations=integrations,
        nango_public_connect_url="https://connect.example",
        nango_public_url="https://nango.example",
    )
    container.nango = (
        NangoClient(
            "http://nango:8080", SECRET, httpx.AsyncClient(transport=httpx.MockTransport(handler))
        )
        if handler
        else None
    )
    return container


def _client(container: _FakeContainer) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for('acme', 'lena')}"},
    )


@pytest.fixture
async def seen() -> AsyncIterator[list[httpx.Request]]:
    yield []


def _nango(seen: list[httpx.Request], connections: list[dict[str, object]]) -> Handler:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.headers["Authorization"] == f"Bearer {SECRET}"
        if request.url.path == "/connect/sessions":
            return httpx.Response(201, json={"data": {"token": "tok-1", "expires_at": "x"}})
        assert request.url.path == "/connection"
        return httpx.Response(200, json={"connections": connections})

    return handle


async def test_a_connect_session_names_the_end_user_and_returns_the_token(
    seen: list[httpx.Request],
) -> None:
    async with _client(_container(_nango(seen, []))) as http:
        got = await http.post("/v1/integrations/connect-session", json={"integration": "microsoft"})

    assert got.status_code == 200
    assert got.json() == {
        "token": "tok-1",
        "connect_url": "https://connect.example",
        "api_url": "https://nango.example",
    }
    sent = json.loads(seen[0].content)
    assert sent["tags"] == {
        "end_user_id": "acme:lena",
        "organization_id": "acme",
        "end_user_display_name": "lena",
    }
    assert sent["allowed_integrations"] == ["microsoft"]
    assert SECRET not in got.text


async def test_an_integration_not_configured_is_a_409_and_asks_nango_nothing(
    seen: list[httpx.Request],
) -> None:
    async with _client(_container(_nango(seen, []))) as http:
        got = await http.post("/v1/integrations/connect-session", json={"integration": "slack"})

    assert got.status_code == 409
    assert seen == []


async def test_connected_only_when_nango_lists_a_connection_for_this_end_user(
    seen: list[httpx.Request],
) -> None:
    listed = [
        {
            "connection_id": "c1",
            "provider_config_key": "microsoft",
            "created": "2026-10-01T09:00:00Z",
        }
    ]
    async with _client(_container(_nango(seen, listed))) as connected:
        yes = await connected.get("/v1/integrations")
    async with _client(_container(_nango([], []))) as bare:
        no = await bare.get("/v1/integrations")

    assert yes.json() == [
        {"integration": "microsoft", "connected": True, "connected_at": "2026-10-01T09:00:00Z"}
    ]
    assert no.json() == [{"integration": "microsoft", "connected": False, "connected_at": None}]
    assert seen[0].url.params["tags[end_user_id]"] == "acme:lena"


async def test_a_connection_on_another_integration_does_not_count(
    seen: list[httpx.Request],
) -> None:
    other = [
        {"connection_id": "c", "provider_config_key": "slack", "created": "2026-10-01T09:00:00Z"}
    ]
    async with _client(_container(_nango(seen, other))) as http:
        got = await http.get("/v1/integrations")

    assert got.json()[0]["connected"] is False


@pytest.mark.parametrize("path", ["/v1/integrations"])
async def test_nango_down_is_a_plain_503_without_the_secret(path: str) -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"refused for {request.headers['Authorization']}")

    async with _client(_container(down)) as http:
        got = await http.get(path)
        posted = await http.post(
            "/v1/integrations/connect-session", json={"integration": "microsoft"}
        )

    assert got.status_code == posted.status_code == 503
    assert SECRET not in got.text + posted.text


async def test_nango_answering_an_error_is_a_503_without_the_secret() -> None:
    async with _client(_container(lambda r: httpx.Response(500, text=SECRET))) as http:
        got = await http.get("/v1/integrations")

    assert got.status_code == 503
    assert SECRET not in got.text


async def test_not_set_up_is_a_503_and_no_integrations_is_an_empty_list() -> None:
    async with _client(_container(None)) as http:
        unset = await http.get("/v1/integrations")
        pressed = await http.post(
            "/v1/integrations/connect-session", json={"integration": "microsoft"}
        )
    async with _client(_container(None, integrations=())) as http:
        none = await http.get("/v1/integrations")

    assert unset.status_code == pressed.status_code == 503
    assert "not set up" in unset.json()["detail"]
    assert none.status_code == 200
    assert none.json() == []


async def test_the_proxy_carries_the_connection_headers_and_the_secret_only_to_nango() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"value": []})

    nango = NangoClient(
        "http://nango:8080/", SECRET, httpx.AsyncClient(transport=httpx.MockTransport(handle))
    )
    got = await nango.proxy(
        "get",
        "/v1.0/me/messages",
        connection_id="c1",
        integration="microsoft",
        params={"$top": "5"},
    )

    assert got.json() == {"value": []}
    sent = seen[0]
    assert (sent.method, sent.url.path, sent.url.params["$top"]) == (
        "GET",
        "/proxy/v1.0/me/messages",
        "5",
    )
    assert sent.headers["Connection-Id"] == "c1"
    assert sent.headers["Provider-Config-Key"] == "microsoft"
    assert sent.headers["Authorization"] == f"Bearer {SECRET}"
