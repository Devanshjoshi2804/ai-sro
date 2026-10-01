"""What went wrong in a chat is kept, through the real `Converse`, `Brain` and tools.

Only the model is scripted. One test per objective signal, then the two promises that matter:
recording never fails or holds up a turn, and no secret is stored.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, cast

from sro.application.execution.workflow_runs import GetWorkflowRun
from sro.domain.chat.brain_turn import BrainReply, ToolCall, ToolResult
from sro.domain.chat.feedback import WITHHELD, Feedback
from sro.domain.prompts.chat_brain import CHAT_BRAIN
from sro.domain.shared.prices import Answer
from tests import factories as f
from tests.unit.application.chat.brain_support import CTX
from tests.unit.application.chat.test_brain_tools import GIVEN, _acting
from tests.unit.application.rig.test_from_the_mail import JOB
from tests.unit.application.test_converse_brain import (
    _call,
    _converse,
    _say,
    _Scripted,
    _thread,
)
from tests.unit.fakes import FakeAsker
from tests.unit.runtime_support import save_job

TENANT = f.TENANT.value
MADE_UP = {"Customer Type": "SR11", "Customer Type Description": "invented by the model"}


def _tools(row: Feedback) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], row.brain["tools"])


def _rows(acting: Any) -> list[Feedback]:
    rows: list[Feedback] = acting.world.uow.chat_feedback.rows
    return rows


async def test_a_value_the_guard_refused_is_kept_with_the_refusal_and_the_tools_called() -> None:
    acting = await _acting()
    asker = FakeAsker(_call("start_job", job_id=JOB, values=MADE_UP), _say("Sorry."))
    converse = _converse(acting, asker, on=(TENANT,))

    thread = await converse.execute(
        CTX, thread_id=await _thread(acting), text="create customer type SR11"
    )

    (row,) = _rows(acting)
    assert (row.kind, row.status, row.operator) == ("guard_refusal", "new", CTX.principal_id.value)
    assert row.message_id == thread.messages[0].id.value and row.thread_id == thread.id.value
    assert row.said == "create customer type SR11"
    assert "is not in what was said" in str(row.other["refusal"])
    (tool,) = _tools(row)
    assert tool["tool"] == "start_job" and tool["ok"] is False
    assert (
        row.brain["prompt"] == f"chat_brain v{CHAT_BRAIN.version}" and row.brain["mode"] == "live"
    )
    assert acting.started == []


async def test_a_turn_that_ran_out_of_budget_is_kept() -> None:
    acting = await _acting()
    asker = FakeAsker(_call("find_jobs", query="customer"), _say("never reached"))
    converse = _converse(acting, asker, on=(TENANT,), max_calls=1)

    await converse.execute(CTX, thread_id=await _thread(acting), text="find customer jobs")

    (row,) = _rows(acting)
    assert row.kind == "budget" and row.other == {"trouble": ["budget"]}


async def test_a_model_fallback_and_unreadable_args_are_kept_as_one_budget_row() -> None:
    acting = await _acting()
    asker = FakeAsker(
        Answer(
            data={"action": "call", "tool": "find_jobs", "args": "[not an object"}, fell_back=True
        ),
        _say("Done."),
    )
    converse = _converse(acting, asker, on=(TENANT,))

    await converse.execute(CTX, thread_id=await _thread(acting), text="find customer jobs")

    (row,) = _rows(acting)
    assert row.kind == "budget" and row.other == {"trouble": ["fell_back", "unreadable_args"]}


async def test_a_clean_turn_keeps_nothing() -> None:
    acting = await _acting()
    converse = _converse(acting, FakeAsker(_say("Hello.")), on=(TENANT,))

    await converse.execute(CTX, thread_id=await _thread(acting), text="hi")

    assert _rows(acting) == []


async def test_two_refusals_in_one_message_keep_one_row() -> None:
    acting = await _acting()
    asker = FakeAsker(
        _call("start_job", job_id=JOB, values=MADE_UP),
        _call("start_job", job_id="mail_nope", values={}),
        _say("Sorry."),
    )
    converse = _converse(acting, asker, on=(TENANT,))

    await converse.execute(CTX, thread_id=await _thread(acting), text="create customer type SR11")

    assert [r.kind for r in _rows(acting)] == ["guard_refusal"]


async def _chat_run(acting: Any, run_id: str = "run_1", offer: str = "chat:msg_1:abc") -> Any:
    run = await acting.world.ran("done", GIVEN, run_id=run_id)
    run = replace(run, offer=offer)
    await acting.world.uow.workflow_runs.save(run)
    return run


async def _deleting() -> Any:
    async def _delete(self: GetWorkflowRun, ctx: Any, run: Any) -> tuple[str, str, str]:
        return "wfl_del", "Customer Type", "SR11"

    GetWorkflowRun.undo_for, was = _delete, GetWorkflowRun.undo_for  # type: ignore[method-assign]
    return was


async def test_taking_back_a_run_the_brain_started_is_kept_however_it_is_asked() -> None:
    acting = await _acting()
    _converse(acting, FakeAsker(), on=(TENANT,))
    await save_job(acting.world.uow, "wfl_del")
    chat = await _chat_run(acting)
    was = await _deleting()
    try:
        # The panel's and the console's Undo is a start under `undoes_run`; the brain's own
        # undo_run is the same start.
        await acting.start.execute(
            CTX,
            workflow_id="wfl_del",
            device_id=None,
            values={"Customer Type": "SR11"},
            live=True,
            allow_focus=True,
            undoes_run=chat.id,
        )
    finally:
        GetWorkflowRun.undo_for = was  # type: ignore[method-assign]

    (row,) = _rows(acting)
    assert (row.kind, row.message_id) == ("undo", "msg_1")
    assert row.brain["started"] == {"run": "run_1", "job": JOB, "values": GIVEN}
    assert str(row.other["undone_by"]).startswith("run_")


async def test_the_brains_own_undo_run_is_kept() -> None:
    acting = await _acting()
    _converse(acting, FakeAsker(), on=(TENANT,))
    await save_job(acting.world.uow, "wfl_del")
    chat = await _chat_run(acting)
    was = await _deleting()
    try:
        result = await acting.undo.run(CTX, {"run_id": chat.id})
    finally:
        GetWorkflowRun.undo_for = was  # type: ignore[method-assign]

    assert result.ok and [(r.kind, r.message_id) for r in _rows(acting)] == [("undo", "msg_1")]


async def test_taking_back_a_run_the_brain_did_not_start_keeps_nothing() -> None:
    acting = await _acting()
    _converse(acting, FakeAsker(), on=(TENANT,))
    await save_job(acting.world.uow, "wfl_del")
    chat = await _chat_run(acting, offer="")
    was = await _deleting()
    try:
        await acting.undo.run(CTX, {"run_id": chat.id})
    finally:
        GetWorkflowRun.undo_for = was  # type: ignore[method-assign]

    assert _rows(acting) == []


async def test_a_failed_run_the_brain_started_is_kept_once_when_the_operator_next_looks() -> None:
    acting = await _acting()
    asker = FakeAsker(_call("run_status"), _say("It failed."), _call("run_status"), _say("Still."))
    converse = _converse(acting, asker, on=(TENANT,))
    thread_id = await _thread(acting)
    await converse.execute(CTX, thread_id=thread_id, text="make SR11")
    made = replace(await acting.world.ran("failed", GIVEN, run_id="run_9"), offer="chat:msg_9:abc")
    await acting.world.uow.workflow_runs.save(made)
    await acting.world.ran("failed", GIVEN, run_id="run_8")

    await converse.execute(CTX, thread_id=thread_id, text="how did it go?")
    await converse.execute(CTX, thread_id=thread_id, text="and now?")

    runs = [r for r in _rows(acting) if r.kind == "run_failed"]
    assert [(r.message_id, r.other["run"], r.other["state"]) for r in runs] == [
        ("msg_9", "run_9", "failed")
    ]


async def test_a_brain_and_a_chain_that_did_different_things_disagree_in_shadow() -> None:
    acting = await _acting()
    asker = FakeAsker(_call("ask_operator", question="Which type?"), _say("Asked."))
    converse = _converse(acting, asker, shadow=(TENANT,))

    thread = await converse.execute(
        CTX, thread_id=await _thread(acting), text="create customer type SR11"
    )
    for later in list(acting.spawned):
        await later

    # The chain offered the job (a start on a yes); the brain would have asked.
    (row,) = _rows(acting)
    assert row.kind == "disagreement" and row.message_id == thread.messages[0].id.value
    assert row.brain["mode"] == "shadow" and row.brain["category"] == "ask"
    assert row.other["category"] == "start" and row.other["reply"]


async def test_a_brain_and_a_chain_that_did_the_same_kind_of_thing_keep_nothing() -> None:
    acting = await _acting()
    asker = FakeAsker(_call("start_job", job_id=JOB, values=GIVEN), _say("Started."))
    converse = _converse(acting, asker, shadow=(TENANT,))

    await converse.execute(
        CTX,
        thread_id=await _thread(acting),
        text="create customer type SR11 with the description new",
    )
    for later in list(acting.spawned):
        await later

    assert _rows(acting) == [] and acting.started == []


async def test_the_comparison_never_holds_up_the_chains_reply() -> None:
    acting = await _acting()
    converse = _converse(acting, FakeAsker(), shadow=(TENANT,))

    thread = await converse.execute(
        CTX, thread_id=await _thread(acting), text="create customer type SR11"
    )

    # The brain's turn is only spawned: the reply is back before it has run.
    assert (thread.messages[-1].decision or {}).get("kind") == "job"
    assert acting.spawned and _rows(acting) == []
    for later in list(acting.spawned):
        later.close()


async def test_a_store_that_is_down_does_not_fail_the_turn() -> None:
    acting = await _acting()
    asker = FakeAsker(_call("start_job", job_id=JOB, values=MADE_UP), _say("Sorry."))
    converse = _converse(acting, asker, on=(TENANT,))
    acting.world.uow.chat_feedback.failing = True

    thread = await converse.execute(
        CTX, thread_id=await _thread(acting), text="create customer type SR11"
    )

    assert thread.messages[-1].text == "Sorry." and _rows(acting) == []


async def test_a_store_that_is_down_does_not_fail_an_undo_or_the_run_status() -> None:
    acting = await _acting()
    _converse(acting, FakeAsker(), on=(TENANT,))
    acting.world.uow.chat_feedback.failing = True
    await save_job(acting.world.uow, "wfl_del")
    chat = await _chat_run(acting)
    was = await _deleting()
    try:
        undone = await acting.undo.run(CTX, {"run_id": chat.id})
    finally:
        GetWorkflowRun.undo_for = was  # type: ignore[method-assign]

    assert undone.ok and len(acting.started) == 1


async def test_no_secret_is_stored() -> None:
    acting = await _acting()
    token = "Bearer " + "a1b2c3d4e5f6a7b8c9d0e1f2a3"
    asker = FakeAsker(
        _call("start_job", job_id=JOB, values={"password": "hunter2", "Customer Type": "SR11"}),
        _say(f"I will not use {token}."),
    )
    converse = _converse(acting, asker, on=(TENANT,))

    await converse.execute(
        CTX,
        thread_id=await _thread(acting),
        text=f"create customer type SR11 with the password hunter2 {token} " + "x" * 600,
    )

    (row,) = _rows(acting)
    kept = json.dumps([row.said, row.brain, row.other])
    assert "hunter2" not in kept and "a1b2c3d4e5f6" not in kept
    assert row.said == WITHHELD
    assert _tools(row)[0]["args"]["values"]["password"] == "<secret>"  # noqa: S105


async def test_a_scripted_reply_with_a_refused_step_is_one_guard_row() -> None:
    acting = await _acting()
    converse = _converse(acting, FakeAsker(), on=(TENANT,))
    refused = ToolResult(False, error="the x you gave is not what you said", guard=True)
    converse._brain = _Scripted(  # type: ignore[assignment]
        BrainReply("No.", (), ((ToolCall("start_job", {"job_id": JOB}), refused),))
    )

    await converse.execute(CTX, thread_id=await _thread(acting), text="x")

    (row,) = _rows(acting)
    assert row.kind == "guard_refusal" and row.other == {"refusal": refused.error}
