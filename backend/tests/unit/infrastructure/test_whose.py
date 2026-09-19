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
