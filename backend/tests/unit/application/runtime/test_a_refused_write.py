"""A write Blue Yonder did not accept keeps what it answered, is settled by
reading its record back, and a refusal is asked about where the job came from.

Seen on QA 2026-09-30 (tenant greyorange): "create Warehouse Equipment Type
PJ26, Voice Code 42" -- 42 already belonged to REACH1, Blue Yonder refused the
save, and the run's step ended unclear, "'Click the save button.' was sent and
nothing confirms it; check it and answer", keeping nothing of the answer.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import replace

from sro.application.chat.ask_the_asker import DRAFTED, DraftForTheAsker
from sro.application.chat.converse import Converse
from sro.application.chat.mailbox import SERVER
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.execution.approvals import Approvals
from sro.application.execution.one_time_secrets import OneTimeSecrets
from sro.application.execution.stops import Stops
from sro.application.execution.workflow_runs import StartWorkflowRun
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.domain.chat.asking import NEEDS, Pending, standing
from sro.domain.chat.thread import Thread
from sro.domain.execution.progress import Progress
from sro.domain.execution.waiting import as_said, waiting_on
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Step, Workflow
from sro.interface.http.schemas import WorkflowRunModel
from tests.unit.application.rig.test_asking_the_asker import THREAD
from tests.unit.application.rig.test_asking_the_asker import _Mailbox as _Asker
from tests.unit.fakes import (
    FakeAsker,
    FakeChannel,
    FakeClock,
    FakeDurableExecution,
    FakeEmbedder,
    FakeHttpCaller,
    FakeIdFactory,
)
from tests.unit.runtime_support import (
    CTX,
    NOW,
    TENANT,
    WORKFLOW,
    SteelRun,
    proven_write_step,
    steel_run,
)

VALUES = {"Customer Type": "GT2", "Description": "Pet shops"}

REFUSED = json.dumps({"errors": [{"message": "Description Pet shops is already used"}]})


def _job() -> tuple[Workflow, tuple[Step, dict[str, Gesture]]]:
    save, saved, _ = proven_write_step(read_back=None, described=("d0", "d1"))
    job = replace(
        WORKFLOW,
        steps=[replace(save, order=0)],
        parameters=[
            {"name": "Customer Type", "seen_values": ["GT0", "GT1"]},
            {"name": "Description", "seen_values": ["d0", "d1"]},
        ],
    )
    return job, (replace(save, order=0), saved)


class _Asking:
    """The run's ask and the chat's answer, wired the way `container.py` wires
    them: `RunSteps.finish` asks through `StartWorkflowRun.ask_for_values`,
    which drafts to the sender through `DraftForTheAsker`."""

    def __init__(self) -> None:
        self.mailbox = _Asker()
        self.start: StartWorkflowRun | None = None

    def wire(self, world: SteelRun) -> StartWorkflowRun:
        drafter = DraftForTheAsker(world.uow, self.mailbox, FakeClock(NOW), FakeIdFactory())

        async def drafts(ctx: RequestContext, run_id: str, pending: Pending, asked: str) -> bool:
            return await drafter.execute(ctx, pending, question=asked, run_id=run_id)

        self.start = StartWorkflowRun(
            world.uow,
            channel=FakeChannel(),
            asker=FakeAsker(),
            clock=FakeClock(NOW),
            cap_usd=5.0,
            stops=Stops(),
            approvals=Approvals(),
            one_time_secrets=OneTimeSecrets(),
            ids=FakeIdFactory(),
            asker_drafts=drafts,
            durable=FakeDurableExecution(),
            steel_tenants=frozenset({TENANT.value}),
        )
        return self.start

    async def __call__(self, ctx: RequestContext, run: WorkflowRun, title: str) -> None:
        assert self.start is not None
        await self.start.ask_for_values(ctx, run, title)

    def converse(self, world: SteelRun) -> Converse:
        return Converse(
            world.uow,
            ResolveIntent(world.uow, PlanTask(Retrieve(world.uow, FakeEmbedder()))),
            FakeClock(NOW),
            FakeIdFactory(),
            start=self.start,
        )


async def _saving(
    *answers: tuple[int, str], asking: _Asking | None = None, mail: dict[str, str] | None = None
) -> tuple[SteelRun, FakeHttpCaller]:
    job, step = _job()
    http = FakeHttpCaller()
    for status, text in answers:
        http.answer(status, text, headers={"content-type": "application/json"})
    world = await steel_run(steps=[step], job=job, values=VALUES, http=http, asks=asking)
    if asking is not None:
        asking.wire(world)
    if mail is not None:
        started = world.uow.workflow_runs.rows[world.run_id]
        started.mail = mail
        started.awaiting = as_said(waiting_on(SERVER, mail["thread"], now=NOW))
    await world.uow.workflows.remember_write(
        TENANT,
        method="POST",
        path_pattern="/api/customer-types",
        origin="https://wms.example",
        run_id="run_proof",
        workflow_id=job.id,
        verified_by="status",
        at="2026-09-21T18:36:07+00:00",
    )
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    return world, http


async def test_a_save_answered_with_a_server_error_keeps_the_status_and_what_it_said() -> None:
    world, _ = await _saving((502, '{"message": "upstream timed out"}'))

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    last = (await world.saved_run()).steps[-1]
    assert last.result is not None
    assert last.result["status"] == "502"
    assert last.result["said"] == "upstream timed out"


async def test_a_clash_whose_record_is_absent_fails_in_its_own_words_and_is_not_redone() -> None:
    world, http = await _saving((409, REFUSED), (404, ""))

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    last = (await world.saved_run()).steps[-1]
    assert last.verdict == "failed", "a refusal the system can read back is not unclear"
    assert "Description Pet shops is already used" in last.reason
    assert "nothing confirms it" not in last.reason
    assert world.lanes.ui.calls == 0, "a refused value was handed to another lane"
    assert [one["method"] for one in http.sent] == ["POST", "GET"]


async def _refused_run(mail: dict[str, str] | None = None) -> tuple[SteelRun, _Asking]:
    asking = _Asking()
    world, _ = await _saving((409, REFUSED), (404, ""), asking=asking, mail=mail)
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    assert not outcome.more and not outcome.asking, "a refusal parked the run on a person"
    assert await world.run_steps.finish(CTX, world.run_id) == "failed"
    return world, asking


async def _chat(world: SteelRun, about: str) -> Thread:
    chat = await ReadThreads(world.uow).asking(CTX, about)
    assert chat is not None, "the refusal has no chat of its own"
    return chat


async def test_a_refusal_ends_the_run_and_asks_for_the_refused_value_in_its_own_chat() -> None:
    world, _ = await _refused_run()

    run = await world.saved_run()
    assert run.needs == ["Description"]
    assert not Progress.of(run.progress).asking, "the run waits on a step question"
    asked = standing((await _chat(world, run.id)).messages)
    assert asked is not None and (asked.decision or {}).get("kind") == NEEDS
    assert "Description Pet shops is already used" in asked.text
    assert "What should Description be?" in asked.text
    assert "could not find" not in asked.text


async def test_a_panel_started_refusal_asks_in_its_chat_and_drafts_no_mail() -> None:
    world, asking = await _refused_run()

    chat = await _chat(world, world.run_id)
    assert [one for one in chat.messages if (one.decision or {}).get("kind") == DRAFTED] == []
    assert asking.mailbox.sent == [], "a run nobody mailed about wrote to somebody"


async def test_the_answer_to_a_refusal_starts_one_new_run_with_the_corrected_value() -> None:
    world, asking = await _refused_run()
    chat = await _chat(world, world.run_id)
    converse = asking.converse(world)

    await asyncio.gather(
        converse.execute(CTX, thread_id=chat.id, text="Vets"),
        converse.execute(CTX, thread_id=chat.id, text="Vets"),
    )

    runs = [one for one in world.uow.workflow_runs.rows.values() if one.id != world.run_id]
    assert len(runs) == 1, "one question started more than one run"
    assert runs[0].values == {"Customer Type": "GT2", "Description": "Vets"}
    failed = await world.saved_run()
    assert failed.outcome == "failed", "the refused run is history, not rewritten"


async def test_a_mail_started_refusal_drafts_a_reply_naming_the_field_and_why() -> None:
    envelope = {"thread": THREAD, "subject": "new customer type", "sender": "tanisha@example.com"}
    world, asking = await _refused_run(mail=envelope)

    chat = await _chat(world, THREAD)
    (draft,) = [one for one in chat.messages if (one.decision or {}).get("kind") == DRAFTED]
    body = str((draft.decision or {}).get("body"))
    assert "Description Pet shops could not be used" in body
    assert "Description Pet shops is already used" in body
    assert "What should Description be instead?" in body
    assert asking.mailbox.sent == [], "the reply went out without the operator"
    run = await world.saved_run()
    assert run.awaiting is None, "a reply would be taken by the ended run, not its question"


async def test_the_run_says_what_it_waits_on_only_while_it_waits() -> None:
    """V1d: the mail card said "Running..." for a run parked on a person."""
    world, _ = await _saving((409, REFUSED), (500, ""))

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    parked = WorkflowRunModel.of(await world.saved_run())
    assert parked.outcome == "running"
    assert "nothing confirms it" in parked.asking
    refused, _ = await _refused_run()
    assert WorkflowRunModel.of(await refused.saved_run()).asking == ""


async def test_a_value_given_in_the_chat_is_carried_and_never_asked_again() -> None:
    """The answer's run keeps what the chat already said: refused again on
    another field, it asks only for that one."""
    world, asking = await _refused_run()
    chat = await _chat(world, world.run_id)
    await asking.converse(world).execute(CTX, thread_id=chat.id, text="Vets")
    (again,) = [one for one in world.uow.workflow_runs.rows.values() if one.id != world.run_id]
    said = (await _chat(world, world.run_id)).messages[-1].text
    assert "Description = Vets (your answer in the chat)" in said
    assert "Customer Type = GT2 (your request)" in said
    again.needs = ["Customer Type"]
    again.outcome = "failed"
    await world.uow.workflow_runs.save(again)
    assert asking.start is not None

    await asking.start.ask_for_values(CTX, again, "Save the customer type")

    asked = standing((await _chat(world, world.run_id)).messages)
    assert asked is not None
    decision = asked.decision or {}
    assert decision.get("missing") == ["Customer Type"]
    assert (decision.get("values") or {}).get("Description") == "Vets"


def _fails_once(asking: _Asking, *, after: bool) -> list[int]:
    """The ask dies once, before it is written or right after (the worker lost)."""
    assert asking.start is not None
    real, calls = asking.start.ask_for_values, [0]

    async def ask(ctx: RequestContext, run: WorkflowRun, title: str) -> None:
        calls[0] += 1
        if after:
            await real(ctx, run, title)
        if calls[0] == 1:
            raise RuntimeError("the worker died")
        if not after:
            await real(ctx, run, title)

    asking.start.ask_for_values = ask  # type: ignore[method-assign]
    return calls


async def _asked_after_a_retry(*, after: bool) -> int:
    asking = _Asking()
    world, _ = await _saving((409, REFUSED), (404, ""), asking=asking)
    _fails_once(asking, after=after)
    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    with contextlib.suppress(RuntimeError):
        await world.run_steps.finish(CTX, world.run_id)
    await world.run_steps.finish(CTX, world.run_id)
    chat = await _chat(world, world.run_id)
    return len([one for one in chat.messages if (one.decision or {}).get("kind") == NEEDS])


async def test_a_retried_finish_still_asks_when_the_first_ask_never_happened() -> None:
    assert await _asked_after_a_retry(after=False) == 1


async def test_a_retried_finish_does_not_ask_again_when_the_question_already_stands() -> None:
    assert await _asked_after_a_retry(after=True) == 1
