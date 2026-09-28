"""A mail job asks its operator who a mail goes to, and only their answer
names anybody: the answer is kept on the job so the next run does not ask."""

from pathlib import Path

import pytest

import sro
from sro.application.context import RequestContext
from sro.application.runtime.answer_run import AnswerRun
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import PrincipalId
from tests.unit.runtime_support import CTX, TENANT, SteelRun, save_step, steel_run

QID = "q_recipient"


async def _asked_who() -> SteelRun:
    world = await steel_run(steps=[save_step(status=201)])
    progress = world.progress()
    progress.asking = {
        "id": QID,
        "kind": "recipient",
        "text": "the mail is addressed outside the conversation: eve@evil.example",
        "step": "0",
    }
    assert await world.uow.workflow_runs.record_progress(TENANT, world.run_id, progress.as_json())
    return world


async def _answer(world: SteelRun, value: str, ctx: RequestContext = CTX) -> None:
    await AnswerRun(world.uow, world.durable).execute(
        ctx, run_id=world.run_id, question_id=QID, value=value
    )


async def test_the_operator_s_answer_names_the_recipient_for_this_job() -> None:
    world = await _asked_who()

    await _answer(world, "Vendor <Vendor@Supplier.example>")
    await world.run_steps.answered(CTX, world.run_id, QID)

    (named,) = await world.uow.workflows.recipients_for(TENANT, (await world.job()).id)
    assert (named.address, named.confirmed_by) == ("vendor@supplier.example", "clerk")
    progress = world.progress()
    assert progress.asking == {} and progress.step == 0, "the step is tried again"


@pytest.mark.parametrize("value", ["", "vendor", "evé@evil.com", "to the vendor, please"])
async def test_an_answer_that_names_no_address_is_refused(value: str) -> None:
    world = await _asked_who()

    with pytest.raises(Conflict):
        await _answer(world, value)

    assert world.durable.answered == []
    assert "answered" not in world.progress().asking


async def test_an_answer_in_words_names_the_addresses_in_them() -> None:
    """Q1: "to devansh.j@..." was refused on QA; a person answers in words."""
    world = await _asked_who()

    await _answer(world, "to A@x.example and b@y.example, a@x.example")

    assert world.progress().asking["address"] == "a@x.example, b@y.example"


async def test_only_the_run_s_own_operator_may_name_a_recipient() -> None:
    world = await _asked_who()
    stranger = RequestContext(tenant_id=TENANT, principal_id=PrincipalId("someone-else"))

    with pytest.raises(Conflict):
        await _answer(world, "vendor@supplier.example", stranger)

    assert world.durable.answered == []


async def test_two_presses_the_first_address_wins() -> None:
    world = await _asked_who()

    await _answer(world, "vendor@supplier.example")
    with pytest.raises(Conflict):
        await _answer(world, "eve@evil.example")
    await _answer(world, "vendor@supplier.example")

    assert world.progress().asking["address"] == "vendor@supplier.example"


async def test_an_answer_carried_out_twice_names_the_recipient_once() -> None:
    """A crash after the recipient is kept and before the question is closed
    carries the answer out again; it is the same row."""
    world = await _asked_who()
    await _answer(world, "vendor@supplier.example")
    answered = world.progress().as_json()

    await world.run_steps.answered(CTX, world.run_id, QID)
    assert await world.uow.workflow_runs.record_progress(TENANT, world.run_id, answered)
    await world.run_steps.answered(CTX, world.run_id, QID)

    job = (await world.job()).id
    assert [one.address for one in await world.uow.workflows.recipients_for(TENANT, job)] == [
        "vendor@supplier.example"
    ]


async def test_a_stopped_run_takes_no_recipient() -> None:
    world = await _asked_who()
    await world.run_steps.stopped(CTX, world.run_id)

    with pytest.raises(Conflict):
        await _answer(world, "vendor@supplier.example")

    assert await world.uow.workflows.recipients_for(TENANT, (await world.job()).id) == ()


def test_only_an_operator_s_answer_names_a_recipient() -> None:
    root = Path(sro.__file__).parent
    writers = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if "confirm_recipient(" in (text := path.read_text(encoding="utf-8"))
        and "def confirm_recipient(" not in text
    )
    assert writers == ["application/execution/mail_job.py"]


async def test_a_run_nobody_started_takes_no_recipient() -> None:
    """A legacy row with no `started_by` has no operator to answer for it."""
    world = await _asked_who()
    run = await world.uow.workflow_runs.get(TENANT, world.run_id)
    assert run is not None
    run.started_by = ""
    await world.uow.workflow_runs.save(run)

    with pytest.raises(Conflict):
        await _answer(world, "vendor@supplier.example")
