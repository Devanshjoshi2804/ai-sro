"""One-click connectors over the real stack: router, use case, NangoClient, and an httpx
MockTransport standing in for Nango.

Nango shapes verified against https://nango.dev/docs/reference/api/connect/sessions/create,
https://nango.dev/docs/reference/api/connection/list and
https://nango.dev/docs/reference/api/proxy/get.
"""

from __future__ import annotations

import hmac
import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from sro.config import Settings
from sro.domain.execution.connector_bearer import sign_bearer, verify_bearer
from sro.domain.execution.secrets import connector_key
from sro.domain.shared.errors import InvariantViolation
from sro.infrastructure.nango.client import NangoClient
from sro.infrastructure.vault.file_vault import FileCredentialVault
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

SECRET = "nango-secret-key-do-not-leak"  # noqa: S105
Handler = Callable[[httpx.Request], httpx.Response]
KEY = "k" * 16 + "signing-key-do-not-leak-" + "0123456789abcdef"  # 56 bytes
LENA = connector_key("acme", "outlook", "lena")


def _container(
    handler: Handler | None,
    integrations: tuple[str, ...] = ("microsoft",),
    signing_key: str | None = KEY,
    linked: bool = True,
) -> _FakeContainer:
    container = _FakeContainer(FakeUnitOfWork())
    if linked:  # the operators these tests are about already pressed Link
        container.vault.secrets[LENA] = sign_bearer(KEY, "outlook", "acme", "lena")
    container.settings = Settings(
        nango_url="http://nango:8080",
        nango_secret_key=SecretStr(SECRET),
        integrations=integrations,
        nango_public_connect_url="https://connect.example",
        nango_public_url="https://nango.example",
        connector_signing_key=signing_key,
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


def _conn(
    connection_id: str,
    integration: str = "microsoft",
    created: str = "2026-10-01T09:00:00Z",
    errors: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "connection_id": connection_id,
        "provider_config_key": integration,
        "created": created,
        "errors": errors or [],
    }


def _nango(
    seen: list[httpx.Request], by_end_user: dict[str, list[dict[str, object]]], page: int = 100
) -> Handler:
    """Nango as the live one behaves: the tag filter is exact, results are paged."""

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.headers["Authorization"] == f"Bearer {SECRET}"
        if request.url.path == "/connect/sessions":
            return httpx.Response(201, json={"data": {"token": "tok-1", "expires_at": "x"}})
        if request.url.path == "/integrations":
            return httpx.Response(
                200, json={"data": [{"unique_key": "microsoft"}, {"unique_key": "slack"}]}
            )
        assert request.url.path == "/connection"
        mine = by_end_user.get(request.url.params["tags[end_user_id]"], [])
        number = int(request.url.params["page"])
        assert request.url.params["limit"] == str(page)
        return httpx.Response(200, json={"connections": mine[number * page : (number + 1) * page]})

    return handle


async def test_a_connect_session_names_the_end_user_and_returns_the_token() -> None:
    seen: list[httpx.Request] = []
    async with _client(_container(_nango(seen, {}))) as http:
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


async def test_an_integration_not_configured_is_a_409_and_asks_nango_nothing() -> None:
    seen: list[httpx.Request] = []
    async with _client(_container(_nango(seen, {}))) as http:
        got = await http.post("/v1/integrations/connect-session", json={"integration": "slack"})

    assert got.status_code == 409
    assert seen == []


async def test_an_operator_sees_only_their_own_connection() -> None:
    seen: list[httpx.Request] = []
    nango = _nango(
        seen,
        {
            "acme:lena": [_conn("c-lena")],
            "acme:bob": [_conn("c-bob", created="2026-09-01T09:00:00Z")],
        },
    )
    async with _client(_container(nango)) as http:
        got = await http.get("/v1/integrations")
    async with _client(_container(_nango([], {"acme:bob": [_conn("c-bob")]}))) as http:
        bare = await http.get("/v1/integrations")

    assert got.json() == [
        {
            "integration": "microsoft",
            "connected": True,
            "connected_at": "2026-10-01T09:00:00Z",
            "available": True,
        }
    ]
    assert bare.json() == [
        {"integration": "microsoft", "connected": False, "connected_at": None, "available": True}
    ]
    assert [r.url.params["tags[end_user_id]"] for r in seen if r.url.path == "/connection"] == [
        "acme:lena"
    ]


async def test_a_connection_on_another_integration_does_not_count() -> None:
    nango = _nango([], {"acme:lena": [_conn("c", "slack")]})
    async with _client(_container(nango)) as http:
        got = await http.get("/v1/integrations")

    assert got.json()[0]["connected"] is False


async def test_a_connection_whose_credentials_fail_is_not_connected() -> None:
    broken = _conn("c1", errors=[{"type": "auth", "log_id": "l"}])
    async with _client(_container(_nango([], {"acme:lena": [broken]}))) as http:
        got = await http.get("/v1/integrations")

    assert got.json()[0]["connected"] is False


async def test_two_connections_report_the_newest_healthy_one_whatever_the_order() -> None:
    old = _conn("old", created="2026-09-01T09:00:00Z")
    new = _conn("new", created="2026-10-02T09:00:00Z")
    newest_but_broken = _conn(
        "bad", created="2026-10-03T09:00:00Z", errors=[{"type": "auth", "log_id": "l"}]
    )
    for order in ([old, new, newest_but_broken], [newest_but_broken, new, old]):
        async with _client(_container(_nango([], {"acme:lena": order}))) as http:
            got = await http.get("/v1/integrations")
        assert got.json()[0]["connected_at"] == "2026-10-02T09:00:00Z"


async def test_every_page_of_connections_is_read() -> None:
    seen: list[httpx.Request] = []
    many = {"acme:lena": [_conn(f"x{i}", "slack") for i in range(5)] + [_conn("last")]}
    client = NangoClient(
        "http://nango:8080",
        SECRET,
        httpx.AsyncClient(transport=httpx.MockTransport(_nango(seen, many, page=2))),
        page_size=2,
    )
    got = await client.connections("acme:lena")

    assert [c.connection_id for c in got][-1] == "last"
    assert len(got) == 6


async def test_nango_down_is_a_plain_503_without_the_secret() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"refused for {request.headers['Authorization']}")

    async with _client(_container(down)) as http:
        got = await http.get("/v1/integrations")
        posted = await http.post(
            "/v1/integrations/connect-session", json={"integration": "microsoft"}
        )

    assert got.status_code == posted.status_code == 503
    assert SECRET not in got.text + posted.text


async def test_nango_answering_an_error_is_a_503_logged_by_status_and_path_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text=SECRET, headers={"X-Echo": SECRET})

    with caplog.at_level("WARNING"):
        async with _client(_container(handle)) as http:
            got = await http.get("/v1/integrations")

    assert got.status_code == 503
    assert "try again shortly" in got.json()["detail"]
    assert SECRET not in got.text + caplog.text
    assert "500" in caplog.text
    assert "/connection" in caplog.text


@pytest.mark.parametrize("refused", [401, 403])
async def test_a_refused_server_key_says_the_server_is_misconfigured(
    refused: int, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("WARNING"):
        async with _client(_container(lambda r: httpx.Response(refused, text=SECRET))) as http:
            got = await http.get("/v1/integrations")

    assert got.status_code == 503
    assert "misconfigured" in got.json()["detail"]
    assert str(refused) in caplog.text
    assert SECRET not in got.text + caplog.text


async def test_the_container_closes_the_nango_client_with_its_other_clients() -> None:
    container = _container(lambda r: httpx.Response(200))
    closed: list[str] = []

    class _Driver:
        async def aclose(self) -> None:
            closed.append("driver")

    container.driver = _Driver()  # type: ignore[assignment]
    assert container.nango is not None

    await container.aclose_clients()

    assert closed == ["driver"]
    assert container.nango._http.is_closed


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


async def test_the_proxy_forwards_headers_to_the_provider_under_nangos_prefix() -> None:
    """Nango passes `Nango-Proxy-<Name>` on to the provider as `<Name>`."""
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    nango = NangoClient(
        "http://nango:8080/", SECRET, httpx.AsyncClient(transport=httpx.MockTransport(handle))
    )
    await nango.proxy(
        "post",
        "/v1.0/me/messages",
        connection_id="c1",
        integration="microsoft",
        headers={"Prefer": 'IdType="ImmutableId"'},
    )

    assert seen[0].headers["Nango-Proxy-Prefer"] == 'IdType="ImmutableId"'
    assert "Prefer" not in seen[0].headers


async def test_a_connection_carries_the_end_user_tag_nango_holds() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        row = {
            "connection_id": "c1",
            "provider_config_key": "microsoft",
            "created": "2026-09-30T00:00:00+00:00",
            "tags": {"end_user_id": "acme:sam"},
        }
        return httpx.Response(200, json={"connections": [row, {**row, "tags": {}}]})

    nango = NangoClient(
        "http://nango:8080/", SECRET, httpx.AsyncClient(transport=httpx.MockTransport(handle))
    )

    first, second = await nango.connections("acme:sam")

    assert (first.end_user_id, second.end_user_id) == ("acme:sam", "")


def _real_vault(container: _FakeContainer, tmp_path: Path) -> FileCredentialVault:
    vault = FileCredentialVault(path=tmp_path / "vault", key=Fernet.generate_key().decode())
    container.vault = vault
    return vault


async def test_linking_keeps_a_bearer_only_the_connector_can_verify(tmp_path: Path) -> None:
    container = _container(_nango([], {"acme:lena": [_conn("c1")]}), signing_key=KEY, linked=False)
    vault = _real_vault(container, tmp_path)
    async with _client(container) as http:
        before = (await http.get("/v1/integrations")).json()[0]["connected"]
        got = await http.post("/v1/integrations/microsoft/link")
        after = (await http.get("/v1/integrations")).json()[0]["connected"]
        again = await http.post("/v1/integrations/microsoft/link")

    kept = await vault.get(LENA)
    assert (before, after) == (False, True)
    assert got.status_code == again.status_code == 200
    assert got.json() == {
        "integration": "microsoft",
        "connected": True,
        "connected_at": "2026-10-01T09:00:00Z",
        "available": True,
    }
    assert kept is not None
    assert verify_bearer(KEY, "outlook", kept) == ("acme", "lena")
    assert verify_bearer(KEY, "gmail", kept) is None
    assert verify_bearer("another-key", "outlook", kept) is None
    assert await vault.get(LENA) == kept  # a second press changes nothing
    assert kept not in got.text + again.text
    assert KEY not in got.text + again.text + kept


async def test_linking_without_a_healthy_connection_is_a_409_and_stores_nothing(
    tmp_path: Path,
) -> None:
    broken = _conn("c1", errors=[{"type": "auth", "log_id": "l"}])
    for found in ([], [broken], [_conn("c2", "slack")]):
        container = _container(_nango([], {"acme:lena": found}), signing_key=KEY, linked=False)
        vault = _real_vault(container, tmp_path)
        async with _client(container) as http:
            got = await http.post("/v1/integrations/microsoft/link")

        assert got.status_code == 409
        assert got.json()["detail"] == "Connect Outlook first"
        assert await vault.get(LENA) is None


async def test_one_operator_cannot_link_another_operators_connection(tmp_path: Path) -> None:
    container = _container(_nango([], {"acme:bob": [_conn("c")]}), signing_key=KEY, linked=False)
    vault = _real_vault(container, tmp_path)
    async with _client(container) as http:
        got = await http.post("/v1/integrations/microsoft/link")

    assert got.status_code == 409
    assert await vault.get(connector_key("acme", "outlook", "bob")) is None


@pytest.mark.parametrize("unset", [None, "", "   "])
async def test_without_a_signing_key_link_is_a_plain_503(unset: str | None) -> None:
    container = _container(_nango([], {"acme:lena": [_conn("c")]}), signing_key=unset, linked=False)
    assert container.settings.connector_signing_key is None
    async with _client(container) as http:
        got = await http.post("/v1/integrations/microsoft/link")

    assert got.status_code == 503
    assert "not set up" in got.json()["detail"]
    assert container.vault.secrets.get(LENA) is None


def test_a_signing_key_shorter_than_32_bytes_is_refused_without_echoing_it() -> None:
    with pytest.raises(ValueError, match="at least 32") as refused:
        Settings(connector_signing_key=SecretStr("short-key-do-not-echo"))
    assert "short-key-do-not-echo" not in str(refused.value)
    assert Settings(connector_signing_key=SecretStr("x" * 32)).connector_signing_key is not None


def test_an_empty_key_neither_signs_nor_verifies() -> None:
    with pytest.raises(InvariantViolation):
        sign_bearer("", "outlook", "acme", "lena")
    forged = f"acme:lena.{hmac.new(b'', b'x', 'sha256').hexdigest()}"
    assert verify_bearer("", "outlook", forged) is None
    assert verify_bearer("", "outlook", sign_bearer(KEY, "outlook", "acme", "lena")) is None


async def test_an_integration_not_configured_cannot_be_linked() -> None:
    container = _container(_nango([], {}), integrations=("slack",))
    async with _client(container) as http:
        got = await http.post("/v1/integrations/microsoft/link")

    assert got.status_code == 409


async def test_linking_an_integration_with_no_connector_has_nothing_to_link() -> None:
    container = _container(
        _nango([], {"acme:lena": [_conn("c", "slack")]}), integrations=("slack",), linked=False
    )
    async with _client(container) as http:
        got = await http.post("/v1/integrations/slack/link")

    assert got.status_code == 200
    assert got.json() == {
        "integration": "slack",
        "connected": True,
        "connected_at": "2026-10-01T09:00:00Z",
        "available": True,
    }
    assert container.vault.secrets == {}


async def test_a_vault_that_is_down_never_leaks_the_bearer_or_key(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    container = _container(_nango([], {"acme:lena": [_conn("c")]}), linked=False)
    _real_vault(container, tmp_path)  # keeps a file this other vault key cannot read
    await container.vault.store("x", "y")
    container.vault = FileCredentialVault(
        path=tmp_path / "vault", key=Fernet.generate_key().decode()
    )
    with caplog.at_level("DEBUG"):
        async with _client(container) as http:
            got = await http.post("/v1/integrations/microsoft/link")

    mac = sign_bearer(KEY, "outlook", "acme", "lena").rpartition(".")[2]
    assert got.status_code >= 500
    assert KEY not in got.text + caplog.text
    assert mac not in got.text + caplog.text


async def test_a_half_linked_account_shows_not_connected(tmp_path: Path) -> None:
    container = _container(_nango([], {"acme:lena": [_conn("c")]}), linked=False)
    _real_vault(container, tmp_path)
    async with _client(container) as http:
        got = await http.get("/v1/integrations")

    assert got.json()[0]["connected"] is False
    assert got.json()[0]["connected_at"] == "2026-10-01T09:00:00Z"


def _flip(mac: str) -> str:
    return f"{int(mac[0], 16) ^ 1:x}{mac[1:]}"  # always a different first character


def test_a_bearer_is_refused_unless_the_mac_matches_for_that_server_and_person() -> None:
    bearer = sign_bearer(KEY, "outlook", "acme", "lena")
    assert bearer.startswith("acme:lena.")
    assert verify_bearer(KEY, "outlook", bearer) == ("acme", "lena")
    mac = bearer.rpartition(".")[2]
    assert _flip(mac) != mac
    for forged in (
        f"acme:bob.{mac}",
        f"other:lena.{mac}",
        f"acme:lena.{_flip(mac)}",
        "acme:lena",
        "acme.lena",
        ".",
        "",
        f"a:b:c.{mac}",
    ):
        assert verify_bearer(KEY, "outlook", forged) is None


def test_ids_that_could_be_framed_two_ways_never_cross_verify() -> None:
    old = hmac.new(KEY.encode(), b"outlook\na\nb\nc", "sha256").hexdigest()  # the bare-newline MAC
    assert verify_bearer(KEY, "outlook", f"a:b\nc.{old}") is None
    assert verify_bearer(KEY, "outlook", f"a\nb:c.{old}") is None
    for tenant, operator in (("a\nb", "c"), ("a", "b\nc"), ("a\x00", "c"), ("a", "b\r")):
        with pytest.raises(InvariantViolation):
            sign_bearer(KEY, "outlook", tenant, operator)
        mac = sign_bearer(KEY, "outlook", "a", "c").rpartition(".")[2]
        assert verify_bearer(KEY, "outlook", f"{tenant}:{operator}.{mac}") is None
    for tenant, operator in (("a:b", "c"), ("a", "b:c"), ("", "c"), ("a", "")):
        with pytest.raises(InvariantViolation):
            sign_bearer(KEY, "outlook", tenant, operator)


def test_the_mac_input_is_unambiguous_for_any_parts() -> None:
    # Same characters, different split: with a bare separator these collided.
    a = sign_bearer(KEY, "outlook", "ab", "c").rpartition(".")[2]
    b = sign_bearer(KEY, "outlook", "a", "bc").rpartition(".")[2]
    c = sign_bearer(KEY, "outlooka", "b", "c").rpartition(".")[2]
    assert len({a, b, c}) == 3


@pytest.mark.parametrize("operator", ["l.ena", "lena.", ".lena", "a.b.c", "léna", "日本", "o'neil"])
def test_any_operator_id_round_trips(operator: str) -> None:
    bearer = sign_bearer(KEY, "outlook", "acmé", operator)
    assert verify_bearer(KEY, "outlook", bearer) == ("acmé", operator)
    assert verify_bearer(KEY, "outlook", bearer + "x") is None


async def test_a_bearer_signed_with_another_key_is_not_connected_and_link_repairs_it(
    tmp_path: Path,
) -> None:
    old_key = "old-" + KEY
    container = _container(_nango([], {"acme:lena": [_conn("c1")]}), signing_key=old_key)
    vault = _real_vault(container, tmp_path)
    async with _client(container) as http:
        await http.post("/v1/integrations/microsoft/link")
        before = (await http.get("/v1/integrations")).json()[0]["connected"]
    container.settings = container.settings.model_copy(
        update={"connector_signing_key": SecretStr(KEY)}
    )
    async with _client(container) as http:
        stale = (await http.get("/v1/integrations")).json()[0]["connected"]
        await http.post("/v1/integrations/microsoft/link")
        repaired = (await http.get("/v1/integrations")).json()[0]["connected"]

    kept = await vault.get(LENA)
    assert (before, stale, repaired) == (True, False, True)
    assert kept is not None
    assert verify_bearer(KEY, "outlook", kept) == ("acme", "lena")


async def test_a_stored_bearer_for_someone_else_or_garbage_is_not_connected() -> None:
    for held in (
        "bearer",
        sign_bearer(KEY, "outlook", "acme", "bob"),
        sign_bearer(KEY, "gmail", "acme", "lena"),
    ):
        container = _container(_nango([], {"acme:lena": [_conn("c")]}))
        container.vault.secrets[LENA] = held
        async with _client(container) as http:
            got = await http.get("/v1/integrations")
        assert got.json()[0]["connected"] is False


async def test_without_a_signing_key_nothing_is_connected() -> None:
    container = _container(_nango([], {"acme:lena": [_conn("c")]}), signing_key=None)
    container.vault.secrets[LENA] = sign_bearer(KEY, "outlook", "acme", "lena")
    async with _client(container) as http:
        got = await http.get("/v1/integrations")

    assert got.json()[0]["connected"] is False


NOT_SET_UP = "Outlook isn't set up on this server yet. An admin adds it in Nango first."


def _nango_without_microsoft(seen: list[httpx.Request]) -> Handler:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/integrations":  # Nango has no integration set up at all
            return httpx.Response(200, json={"data": []})
        if request.url.path == "/connect/sessions":  # what the live one answered on QA
            return httpx.Response(400, json={"error": {"code": "invalid_body", "message": SECRET}})
        return httpx.Response(200, json={"connections": []})

    return handle


async def test_an_integration_nango_does_not_have_is_listed_as_unavailable() -> None:
    async with _client(_container(_nango_without_microsoft([]))) as http:
        got = await http.get("/v1/integrations")

    assert got.status_code == 200
    assert got.json() == [
        {"integration": "microsoft", "connected": False, "connected_at": None, "available": False}
    ]


@pytest.mark.parametrize("answer", [400, 404])
async def test_connecting_an_integration_nango_does_not_have_is_a_plain_409(
    answer: int, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("WARNING"):
        async with _client(_container(lambda r: httpx.Response(answer, text=SECRET))) as http:
            got = await http.post(
                "/v1/integrations/connect-session", json={"integration": "microsoft"}
            )

    assert got.status_code == 409
    assert got.json()["detail"] == NOT_SET_UP
    assert SECRET not in got.text + caplog.text
    assert str(answer) in caplog.text


async def test_linking_an_integration_nango_does_not_have_is_the_same_409(tmp_path: Path) -> None:
    container = _container(_nango_without_microsoft([]), signing_key=KEY, linked=False)
    vault = _real_vault(container, tmp_path)
    async with _client(container) as http:
        got = await http.post("/v1/integrations/microsoft/link")

    assert got.status_code == 409
    assert got.json()["detail"] == NOT_SET_UP
    assert await vault.get(LENA) is None


async def test_connect_session_with_nango_down_or_refusing_the_key_is_unchanged() -> None:
    async with _client(_container(lambda r: httpx.Response(502))) as http:
        down = await http.post(
            "/v1/integrations/connect-session", json={"integration": "microsoft"}
        )
    async with _client(_container(lambda r: httpx.Response(401))) as http:
        refused = await http.post(
            "/v1/integrations/connect-session", json={"integration": "microsoft"}
        )

    assert down.status_code == refused.status_code == 503
    assert "try again shortly" in down.json()["detail"]
    assert "misconfigured" in refused.json()["detail"]
