"""The scenario harness: its fake world, its runner and its checker, with a scripted model.

Nothing here calls a model or reads a database.
"""

from __future__ import annotations

from typing import Any

import pytest
from evals.scenarios.harness import DELETE, World, fake_tools

from sro.application.context import RequestContext
from sro.domain.chat.brain_turn import ToolResult, Turn
from sro.domain.shared.identifiers import PrincipalId, TenantId

CTX = RequestContext(tenant_id=TenantId("eval"), principal_id=PrincipalId("eval"))
CREATE = "Create a Customer Type"
SRT9 = {"Customer Type": "SRT9", "Customer Type Description": "nine"}


async def _use(world: World, tool: str, said: str = "", offer: str = "", **args: Any) -> ToolResult:
    one = next(t for t in fake_tools(world) if t.name == tool)
    return await one.run(CTX, args, Turn(said=said, offer=offer))


def _customer(world: World) -> str:
    return world.id_of(CREATE)


@pytest.mark.asyncio
async def test_a_start_checks_as_the_real_one_and_records_instead_of_launching() -> None:
    world = World()
    job = _customer(world)
    said = "create customer type SRT9 with description nine"
    # a value the operator never said is refused by the real check
    refused = await _use(world, "start_job", said, job_id=job, values={**SRT9, "Department": "Ops"})
    assert not refused.ok and "Department" in refused.error and not world.launches
    started = await _use(world, "start_job", said, "chat:m1", job_id=job, values=SRT9)
    assert started.ok and started.ends_turn and [one.job for one in world.launches] == [CREATE]
    # the same message again is the same run; so is the same start in another message
    for offer in ("chat:m1", "chat:m2"):
        again = await _use(world, "start_job", said, offer, job_id=job, values=SRT9)
        assert again.data["state"] == "already running"
    assert len(world.launches) == 1


@pytest.mark.asyncio
async def test_a_mail_job_is_refused_and_an_unknown_job_too() -> None:
    world = World()
    mail = await _use(world, "start_job", "x", job_id="mail_send", values={})
    assert "sends mail" in mail.error
    assert "not a job this team has" in (await _use(world, "start_job", "x", job_id="nope")).error
    assert not world.launches


@pytest.mark.asyncio
async def test_a_run_in_the_world_is_already_running() -> None:
    world = World({"runs": [{"id": "run_b2", "job": CREATE, "state": "running", "values": SRT9}]})
    said = "create customer type SRT9 with description nine"
    again = await _use(world, "start_job", said, "chat:m1", job_id=_customer(world), values=SRT9)
    assert again.data["state"] == "already running" and not world.launches


@pytest.mark.asyncio
async def test_run_status_shows_the_real_row_shape() -> None:
    world = World(
        {
            "runs": [
                {"id": "run_c3", "job": CREATE, "state": "failed", "values": SRT9, "reason": "no"}
            ]
        }
    )
    row = (await _use(world, "run_status")).data["runs"][0]  # type: ignore[index]
    assert row["job"] == _customer(world) and row["state"] == "failed"
    assert row["stopped_because"] == "no" and row["from_mail"] is False


@pytest.mark.asyncio
async def test_mail_is_read_once_automated_mail_is_ignored_and_a_down_mailbox_fails() -> None:
    mail = [
        {"from": "a@x.com", "subject": "New", "body": "make SRT9"},
        {"from": "mailer-daemon@x.com", "subject": "bounce", "body": "gone"},
    ]
    world = World({"mail": mail})
    first = await _use(world, "check_mail")
    said = str(first.data["said"])
    assert "make SRT9" in said and "bounce" not in said and first.data["read"] == 2
    assert "no mail has arrived" in str((await _use(world, "check_mail")).data["said"])
    assert not (await _use(World({"mail_down": True}), "check_mail")).ok


@pytest.mark.asyncio
async def test_lookup_work_and_ask() -> None:
    world = World({"lookup": "KKYT exists"})
    assert (await _use(world, "lookup", question="q")).data["answer"] == "KKYT exists"
    assert (await _use(World(), "lookup", question="q")).error == "nothing found"
    await _use(world, "work_it_out", task="open putaway")
    assert world.works == ["open putaway"] and not world.launches
    asked = await _use(world, "ask_operator", question="Which code?")
    assert asked.decision == {"kind": "brain_asks", "question": "Which code?"}


@pytest.mark.asyncio
async def test_only_a_done_create_run_can_be_undone_once() -> None:
    runs = [
        {"id": "run_a1", "job": CREATE, "state": "done", "values": SRT9},
        {"id": "run_b2", "job": CREATE, "state": "running", "values": SRT9},
        {"id": "run_c3", "job": CREATE, "state": "failed", "values": SRT9},
    ]
    world = World({"runs": runs})
    for refused in ("run_b2", "run_c3", "run_none"):
        assert not (await _use(world, "undo_run", run_id=refused)).ok
    done = await _use(world, "undo_run", run_id="run_a1")
    assert done.ok and [(one.job, one.via) for one in world.launches] == [(DELETE, "undo")]
    assert not (await _use(world, "undo_run", run_id="run_a1")).ok
