"""The worker's only way to reach a browser, and what it puts on the wire.

`ApiRunDispatcher` had no tests at all. It is the one thing standing between a
schedule that fired inside the Temporal worker and an operator's Chrome, which
is held by whichever process the extension connected to -- and every field it
sends is a field that would be wrong only in production.

Deliberately the public endpoints and no others. An internal "send this browser
a command" route would be a way to drive somebody's signed-in session anywhere.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol

import httpx
import pytest

from sro.application.context import RequestContext
from sro.application.ports.auth import Caller
from sro.application.ports.dispatch import DispatchFailed
from sro.domain.execution.run import Medium
from sro.domain.shared.identifiers import DeviceId, PrincipalId, SkillId, TenantId
from sro.infrastructure.http.api_runs import CREDENTIAL_HOURS, ApiRunDispatcher

TENANT = TenantId("acme")
WHO = PrincipalId("supervisor-9")
CTX = RequestContext(tenant_id=TENANT, principal_id=WHO)
LAPTOP = DeviceId("dev-1")


class _Minted:
    """Records who a credential was minted for, and for how long."""

    def __init__(self) -> None:
        self.issued: list[tuple[Caller, float]] = []

    def verify(self, presented: str) -> Caller:
        raise NotImplementedError

    def issue(self, caller: Caller, *, lasting_hours: float) -> str:
        self.issued.append((caller, lasting_hours))
        return "minted-token"


class _Sent:
    """One captured request, and the answer the API gave back."""

    def __init__(self, status: int = 201, body: object | None = None) -> None:
        self.status = status
        self.body = {"id": "run_1"} if body is None else body
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status, json=self.body)

    @property
    def only(self) -> httpx.Request:
        (one,) = self.requests
        return one

    @property
    def json(self) -> dict[str, object]:
        loaded = json.loads(self.only.content)
        assert isinstance(loaded, dict)
        return loaded


class _Builds(Protocol):
    def __call__(
        self, handler: _Sent, *, minted: _Minted | None = None, base_url: str = ...
    ) -> ApiRunDispatcher: ...


def _answering(handler: Callable[[httpx.Request], httpx.Response]) -> Callable[..., Any]:
    """A stand-in for `httpx.AsyncClient` that answers from `handler`.

    Patched onto the module rather than injected into the dispatcher: the name
    is looked up at call time, so this reaches the client built inside the
    dispatcher's own `async with` without giving production code a seam that
    exists only for a test.
    """
    real = httpx.AsyncClient

    def fake(**kwargs: Any) -> httpx.AsyncClient:
        return real(transport=httpx.MockTransport(handler), **kwargs)

    return fake


@pytest.fixture
def dispatcher(monkeypatch: pytest.MonkeyPatch) -> _Builds:
    def build(
        handler: _Sent, *, minted: _Minted | None = None, base_url: str = "https://api.test/"
    ) -> ApiRunDispatcher:
        monkeypatch.setattr(httpx, "AsyncClient", _answering(handler))
        return ApiRunDispatcher(base_url, minted or _Minted())

    return build


async def test_a_skill_run_is_asked_for_at_the_door_a_person_would_use(dispatcher: _Builds) -> None:
    sent = _Sent()
    asking = dispatcher(sent)

    run_id = await asking.start(
        CTX,
        skill_id=SkillId("skl-1"),
        parameters={"shipment_id": "12345"},
        device_id=LAPTOP,
        version=3,
        authorized_by=True,
        medium=Medium.UI,
        may_take_focus=True,
    )

    assert run_id.value == "run_1"
    assert str(sent.only.url) == "https://api.test/v1/skills/skl-1/runs"
    assert sent.json == {
        "parameters": {"shipment_id": "12345"},
        "version": 3,
        "medium": "ui",
        "device_id": "dev-1",
        "may_take_focus": True,
        "authorized_by": "supervisor-9",
    }


async def test_a_job_is_asked_for_live_at_the_workflow_runs_door(dispatcher: _Builds) -> None:
    """Live, always, and the body says so rather than leaving it to a default.

    A dry run of a scheduled job sends nothing and verifies nothing -- it is a
    trigger that appears to work. What keeps a live one safe is the ladder the
    run climbs, not dryness.
    """
    sent = _Sent()
    asking = dispatcher(sent)

    run_id = await asking.start_job(
        CTX,
        workflow_id="wfl_1",
        device_id=LAPTOP,
        values={"clientCode": "NEWTESTS"},
        allow_focus=False,
    )

    assert run_id.value == "run_1"
    assert str(sent.only.url) == "https://api.test/v1/workflow-runs"
    assert sent.json == {
        "workflow_id": "wfl_1",
        "device_id": "dev-1",
        "values": {"clientCode": "NEWTESTS"},
        "live": True,
        "allow_focus": False,
    }
    # No `started_by`. The API reads the starter off the credential, and a
    # request that names its own authoriser is a signature nobody checked.
    assert "started_by" not in sent.json


async def test_the_credential_is_minted_for_the_trigger_principal_and_dies_in_minutes(
    dispatcher: _Builds,
) -> None:
    sent, minted = _Sent(), _Minted()
    asking = dispatcher(sent, minted=minted)

    await asking.start_job(CTX, workflow_id="wfl_1", device_id=LAPTOP, values={})

    assert sent.only.headers["authorization"] == "Bearer minted-token"
    (caller, hours) = minted.issued[0]
    assert caller.tenant_id == TENANT
    assert caller.principal_id == WHO
    # Long enough to make one call, short enough that a copy found in a log
    # later is worth nothing.
    assert hours == CREDENTIAL_HOURS
    assert hours * 60 <= 5


async def test_an_api_that_refuses_says_why_rather_than_only_how(dispatcher: _Builds) -> None:
    # A status code on its own sends whoever reads the log to the wrong place.
    sent = _Sent(status=409, body={"detail": "dev-1 is not connected"})
    asking = dispatcher(sent)

    with pytest.raises(DispatchFailed, match="not connected"):
        await asking.start_job(CTX, workflow_id="wfl_1", device_id=LAPTOP, values={})


async def test_a_run_started_without_an_id_is_not_a_run_anybody_can_watch(
    dispatcher: _Builds,
) -> None:
    sent = _Sent(body={"status": "running"})
    asking = dispatcher(sent)

    with pytest.raises(DispatchFailed, match="without an id"):
        await asking.start_job(CTX, workflow_id="wfl_1", device_id=LAPTOP, values={})


async def test_an_api_that_cannot_be_reached_is_a_dispatch_failure_not_a_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(httpx, "AsyncClient", _answering(refuse))

    with pytest.raises(DispatchFailed, match="could not be handed"):
        await ApiRunDispatcher("https://api.test", _Minted()).start_job(
            CTX, workflow_id="wfl_1", device_id=LAPTOP, values={}
        )
