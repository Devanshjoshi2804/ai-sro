"""Whose work a log line is about.

A line that says what happened and not who it happened to is unattributable
the moment a deployment has more than one tenant -- and the question somebody
asks is never "did a mining pass refuse something", it is "this operator
pressed that button and nothing happened".
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

import pytest

from sro.infrastructure.telemetry.whose import (
    AsJson,
    Attribution,
    Louder,
    Plainly,
    about,
    attribute,
    whose,
)


def _record(said: str = "a job was refused") -> logging.LogRecord:
    record = logging.LogRecord("sro.mining", logging.INFO, __file__, 1, said, (), None)
    Attribution().filter(record)
    return record


def test_a_line_written_outside_any_work_is_attributed_to_nobody() -> None:
    assert whose() == {}
    assert "[" not in Plainly("%(message)s").format(_record())


def test_a_line_carries_whose_work_it_was() -> None:
    with about(tenant="greyorange", run="run_4a57baf0"):
        said = Plainly("%(message)s").format(_record())

    assert "tenant=greyorange" in said
    assert "run=run_4a57baf0" in said


def test_the_work_inside_work_keeps_both_and_gives_back_what_it_found() -> None:
    """A run inside a request is the request's tenant and its own run id, and
    the request goes on being itself afterwards."""
    with about(tenant="greyorange", request="req_abc"):
        with about(run="run_1", step=3):
            assert whose() == {
                "tenant": "greyorange",
                "request": "req_abc",
                "run": "run_1",
                "step": 3,
            }
        assert whose() == {"tenant": "greyorange", "request": "req_abc"}
    assert whose() == {}


def test_nothing_is_not_an_attribution() -> None:
    """So a caller may pass an id it may not have without a conditional."""
    with about(tenant="greyorange", run=None):
        assert whose() == {"tenant": "greyorange"}


def test_a_line_may_not_be_attributed_to_just_anything() -> None:
    """This plane leaves the building, so the refusal lands on whoever added
    the field rather than on whoever reads the logs six months later."""
    with pytest.raises(ValueError, match="customer_name"), about(customer_name="ACME"):
        pass


def test_json_carries_the_attribution_where_a_collector_can_index_it() -> None:
    with about(tenant="greyorange", run="run_1", step=2):
        said = json.loads(AsJson().format(_record()))

    assert said["tenant"] == "greyorange"
    assert said["run"] == "run_1"
    assert said["step"] == 2
    assert said["said"] == "a job was refused"
    assert said["level"] == "INFO"


def test_json_says_what_blew_up() -> None:
    try:
        raise RuntimeError("the warehouse refused")
    except RuntimeError:
        record = logging.LogRecord(
            "sro.mining", logging.ERROR, __file__, 1, "it failed", (), sys.exc_info()
        )
    Attribution().filter(record)

    said = json.loads(AsJson().format(record))

    assert "the warehouse refused" in said["blew_up"]


async def test_one_task_does_not_attribute_another_task_s_lines() -> None:
    """What makes `attribute` sound: asyncio copies the context into a task, so
    a run that sets its own id cannot put it on a sibling's lines."""
    seen: dict[str, dict[str, object]] = {}

    async def a_run(name: str) -> None:
        attribute(run=name)
        await asyncio.sleep(0)
        seen[name] = whose()

    await asyncio.gather(a_run("run_one"), a_run("run_two"))

    assert seen["run_one"] == {"run": "run_one"}
    assert seen["run_two"] == {"run": "run_two"}
    assert whose() == {}, "and the caller is still attributed to nobody"


# --- the door: what a request says about itself ------------------------------


async def test_a_request_carries_who_asked_from_the_moment_it_is_known() -> None:
    """The middleware gives a request an id before anything knows who is
    asking; `get_context` is the first moment anything does, and `asking_device`
    the first moment a browser has proved it is itself.

    Asserted as an ordering rather than by driving FastAPI: what matters is
    that each attribution lands and that leaving the request takes them all
    with it, which is the property a multi-tenant deployment depends on.
    """
    seen: list[dict[str, object]] = []

    async def one_request(tenant: str, principal: str) -> None:
        with about(request=f"req_{tenant}"):
            attribute(tenant=tenant, principal=principal)
            await asyncio.sleep(0)
            attribute(device=f"dev_{tenant}")
            seen.append(whose())

    await asyncio.gather(
        one_request("greyorange", "rudy"),
        one_request("acme", "someone-else"),
    )

    by_tenant = {one["tenant"]: one for one in seen}
    assert by_tenant["greyorange"] == {
        "request": "req_greyorange",
        "tenant": "greyorange",
        "principal": "rudy",
        "device": "dev_greyorange",
    }
    assert by_tenant["acme"]["principal"] == "someone-else", "no tenant wore another's"
    assert whose() == {}, "and nothing outlived either request"


# --- a door that refuses says so --------------------------------------------


def test_every_refusal_this_api_makes_is_said_out_loud() -> None:
    """Each of the three renderers, because each is reached by a different kind
    of failure and a record kept in one of them is a record missing from the
    other two.

    A refusal used to answer a problem document and leave no trace behind it.
    An operator whose button did nothing has a refusal with a reason in it, and
    the only copy of that reason was in their browser.

    Through a real handler rather than `caplog`: what is being asserted is that
    the attribution reaches a record on its way out, and that happens in a
    handler's own filter.
    """
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError

    from sro.domain.shared.errors import NotFound
    from sro.interface.http.errors import _http_problem, _problem, _validation_problem

    class _Ask:
        method = "POST"
        url = type("U", (), {"path": "/v1/threads/thr_1/messages"})()

    kept: list[logging.LogRecord] = []

    class _Kept(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            kept.append(record)

    handler = _Kept()
    handler.addFilter(Attribution())
    logger = logging.getLogger("sro.interface.http.errors")
    logger.addHandler(handler)
    was = logger.level
    logger.setLevel(logging.WARNING)
    try:
        asked = _Ask()
        with about(tenant="greyorange", principal="rudy", request="req_1"):
            _problem(asked, NotFound("no such thread"))
            _http_problem(asked, HTTPException(status_code=404, detail="device was not found"))
            _validation_problem(asked, RequestValidationError([]))
    finally:
        logger.removeHandler(handler)
        logger.setLevel(was)

    said = [record.getMessage() for record in kept]
    assert len(said) == 3, said
    assert all("refused" in one and "/v1/threads/thr_1/messages" in one for one in said), said
    assert "no such thread" in said[0]
    assert "device was not found" in said[1]
    # And each one names who was refused, without any of the three being told.
    assert all(record.whose["tenant"] == "greyorange" for record in kept)  # type: ignore[attr-defined]
    assert all(record.whose["principal"] == "rudy" for record in kept)  # type: ignore[attr-defined]


def test_a_server_fault_is_louder_than_a_caller_s_mistake(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from fastapi import HTTPException

    from sro.interface.http.errors import _http_problem

    class _Ask:
        method = "GET"
        url = type("U", (), {"path": "/v1/skills"})()

    with caplog.at_level(logging.INFO, logger="sro.interface.http.errors"):
        _http_problem(_Ask(), HTTPException(status_code=404, detail="gone"))
        _http_problem(_Ask(), HTTPException(status_code=503, detail="no vault"))

    assert [record.levelno for record in caplog.records] == [logging.WARNING, logging.ERROR]


# --- one tenant louder than the rest ------------------------------------------


def test_one_tenant_can_be_turned_up_without_turning_everything_up() -> None:
    """A deployment asked what happened to one customer had two choices and
    both are bad: the whole process at DEBUG -- every tenant, every sweep,
    every query, for as long as it takes to reproduce -- or nothing.

    The attribution is what makes the third option possible: the record already
    knows whose it is by the time a filter sees it.
    """
    loud = Louder(logging.INFO, frozenset({"greyorange"}))

    def seen(level: int, tenant: str | None) -> bool:
        record = logging.LogRecord("sro.mining", level, __file__, 1, "a thing", (), None)
        with about(tenant=tenant):
            Attribution().filter(record)
        return loud.filter(record)

    assert seen(logging.DEBUG, "greyorange") is True, "the tenant asked for"
    assert seen(logging.DEBUG, "acme") is False, "and not the one beside it"
    assert seen(logging.DEBUG, None) is False, "nor work belonging to nobody"
    # Everything at or above the floor comes through however it is attributed.
    assert seen(logging.INFO, "acme") is True
    assert seen(logging.WARNING, None) is True


def test_with_nobody_named_nothing_below_the_floor_gets_through() -> None:
    """The ordinary case, and the one a deployment runs in."""
    loud = Louder(logging.INFO, frozenset())
    record = logging.LogRecord("sro.mining", logging.DEBUG, __file__, 1, "a thing", (), None)

    with about(tenant="greyorange"):
        Attribution().filter(record)

    assert loud.filter(record) is False
