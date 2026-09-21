"""One line per request, with whoever it turned out to be on it.

uvicorn writes its access line from the protocol layer once the response is
done, outside the task the handlers ran in: a path, a status and nobody at
all. On a deployment with twenty tenants that made the one line written for
every request the one line that could not be attributed to any of them.
"""

from __future__ import annotations

import logging

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from sro.interface.http.app import Attributing
from sro.whose import Attribution, attribute, whose


def _served() -> FastAPI:
    app = FastAPI()

    async def credentialled() -> None:
        # What `deps.get_context` does: the tenant and the principal come off
        # the credential, inside the request, long after any middleware. Async
        # for the reason that one is -- FastAPI runs a SYNC dependency in a
        # threadpool with a COPY of the context, and the copy is thrown away.
        attribute(tenant="greyorange", principal="rudy")

    @app.get("/thing", dependencies=[Depends(credentialled)])
    def thing() -> dict[str, str]:
        return {"said": str(whose().get("request", ""))}

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(Attributing)
    return app


@pytest.fixture(autouse=True)
def _attributed(caplog: pytest.LogCaptureFixture) -> None:
    """What the real handler carries. In the deployment the filter is on the
    handler `observability` installs, so the ids reach the formatter; caplog
    brings its own handler and would otherwise show a record with the message
    and nothing on it."""
    caplog.handler.addFilter(Attribution())


def test_the_line_carries_whoever_the_route_turned_out_to_be(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The whole reason `Attributing` is a pure ASGI class rather than an
    `@app.middleware("http")` function: Starlette runs an http middleware's
    downstream app in a SEPARATE task, so every id a route establishes is set
    in a context that middleware never sees."""
    with caplog.at_level(logging.INFO, logger="sro.http"):
        assert TestClient(_served()).get("/thing").status_code == 200

    [line] = [one for one in caplog.records if one.name == "sro.http"]
    assert "GET /thing 200" in line.getMessage()
    whose_line: dict[str, object] = line.whose
    assert whose_line == {
        "tenant": "greyorange",
        "principal": "rudy",
        "request": whose_line["request"],
    }


def test_the_request_id_the_client_sent_is_the_one_on_the_line(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A console and an extension that carry `x-request-id` through can be
    joined to what the backend did with it, which is the join somebody
    debugging a button actually needs."""
    with caplog.at_level(logging.INFO, logger="sro.http"):
        said = TestClient(_served()).get("/thing", headers={"x-request-id": "req_theirs"})

    assert said.json() == {"said": "req_theirs"}
    [line] = [one for one in caplog.records if one.name == "sro.http"]
    assert line.whose["request"] == "req_theirs"


def test_the_health_check_is_not_six_thousand_lines_a_day(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Still written, because a deployment where it STOPS is one somebody
    wants the record of. Not at the level somebody is reading."""
    with caplog.at_level(logging.DEBUG, logger="sro.http"):
        TestClient(_served()).get("/health")

    [line] = [one for one in caplog.records if one.name == "sro.http"]
    assert line.levelno == logging.DEBUG, "the health check is in the way of the log"


def test_a_request_that_never_answered_is_still_a_line(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The one somebody is looking for. A handler that raised before anything
    started a response used to leave nothing at all behind it."""
    app = FastAPI()

    @app.get("/broken")
    def broken() -> None:
        raise RuntimeError("no")

    app.add_middleware(Attributing)

    with caplog.at_level(logging.INFO, logger="sro.http"):  # noqa: SIM117
        with pytest.raises(RuntimeError):
            TestClient(app).get("/broken")

    [line] = [one for one in caplog.records if one.name == "sro.http"]
    assert "no answer" in line.getMessage(), line.getMessage()


def test_every_dependency_that_attributes_is_awaited_rather_than_threaded() -> None:
    """The defect that made all of this invisible.

    FastAPI runs a SYNC dependency in a threadpool, and `run_in_threadpool`
    hands it a COPY of the context. `attribute` there sets the tenant in the
    copy, the thread finishes, the copy is thrown away -- and every line the
    request goes on to write carries a request id and nobody. `get_context`
    was that dependency, which is every credentialled route in the system.

    Read off the source rather than by driving each route: what is asserted is
    that no dependency ANYWHERE attributes from a thread, which no amount of
    exercising the routes I happen to think of can establish.
    """
    import ast
    from pathlib import Path

    threaded: list[str] = []
    for door in Path("src/sro/interface/http").rglob("*.py"):
        tree = ast.parse(door.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if any(
                isinstance(call.func, ast.Name) and call.func.id == "attribute"
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
            ):
                threaded.append(f"{door.name}:{node.name}")

    assert threaded == [], (
        f"these attribute from a threadpool, where the context is a copy nobody reads: {threaded}"
    )


async def test_a_browser_that_proved_itself_is_on_the_line() -> None:
    """Every `/v1/agents/{device_id}/...` route carries the device in its path
    and carried it on none of its log lines: they take `device_id: str` and
    prove it in the handler, so `asking_device` -- which attributes for the
    query-string case -- never ran.

    Attributed where they all prove it, and only after they have. A line
    attributing work to a browser that FAILED to prove it is worse than one
    attributing it to nobody.
    """
    from sro.application.context import RequestContext
    from sro.application.observation.register import ReadDevice, RegisterDevice
    from sro.domain.shared.errors import NotFound
    from sro.domain.shared.identifiers import PrincipalId, TenantId
    from tests.unit.fakes import FakeClock, FakeIdFactory, FakeUnitOfWork

    ctx = RequestContext(tenant_id=TenantId("greyorange"), principal_id=PrincipalId("rudy"))
    uow = FakeUnitOfWork()
    registered = await RegisterDevice(uow, FakeClock(), FakeIdFactory()).execute(
        ctx, label="laptop", extension_version="0.1.0"
    )

    wrong = "not the one this browser was minted"
    with pytest.raises(NotFound):
        await ReadDevice(uow).execute(ctx, device_id=registered.device_id, secret=wrong)
    assert "device" not in whose(), "a browser that failed to prove itself was attributed anyway"

    await ReadDevice(uow).execute(ctx, device_id=registered.device_id, secret=registered.secret)

    assert whose()["device"] == registered.device_id.value
