"""The brain answers for the tenants that are switched on, and only reads for the shadowed ones.

Every test goes through `Converse.execute` with the real `Brain` and the real
tools over the fakes; only the model is scripted. The fast paths (a yes to an
open offer) stay model-free, and a tenant that is not listed is the old chain.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest

from sro.application.chat.brain import Brain
from sro.application.chat.brain_tools import brain_tools
from sro.application.chat.converse import Converse, StartThread
from sro.application.execution.workflow_runs import GetWorkflowRun
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.application.observation.record_attempt import RecordAttempt
from sro.config import Settings
from sro.domain.chat.brain_turn import BrainReply, ToolCall, ToolResult
from sro.domain.observation.attempts import DONE, REFUSED
from sro.domain.shared.prices import Answer
from tests import factories as f
from tests.unit.application.chat.brain_support import CTX
from tests.unit.application.chat.test_brain_tools import GIVEN, _Acting, _acting
from tests.unit.application.rig.test_from_the_mail import JOB
from tests.unit.application.test_converse import _PlacesTheJob, _understood
from tests.unit.fakes import FakeAsker, FakeEmbedder, FakeIdFactory

TENANT = f.TENANT.value


def _call(tool: str, **args: object) -> Answer:
    return Answer(data={"action": "call", "tool": tool, "args": json.dumps(args)})


def _say(text: str) -> Answer:
    return Answer(data={"action": "say", "text": text})


def _converse(
    acting: _Acting,
    asker: FakeAsker,
    *,
    on: tuple[str, ...] = (),
    shadow: tuple[str, ...] = (),
) -> Converse:
    world = acting.world
    tools = brain_tools(
        uow=world.uow,
        clock=world.clock,
        runs=world.runs,
        run=GetWorkflowRun(world.uow),
        threads=world.threads,
        look_mail=world.look,
        look_up=None,
        start=acting.start,
        plan=PlanTask(Retrieve(world.uow, FakeEmbedder())),
        spawn=acting.spawned.append,
    )
    return Converse(
        world.uow,
        ResolveIntent(world.uow, PlanTask(Retrieve(world.uow, FakeEmbedder()))),
        world.clock,
        FakeIdFactory(),
        reads_jobs=_PlacesTheJob(_understood(JOB, values=GIVEN)),
        start=acting.start,
        spawn=acting.spawned.append,
        attempts=RecordAttempt(world.uow, FakeIdFactory(), world.clock),
        brain=Brain(world.uow, asker, world.clock, tools, cap_usd=5.0),
        brain_tenants=frozenset(on),
        brain_shadow_tenants=frozenset(shadow),
    )


async def _thread(acting: _Acting) -> Any:
    started = StartThread(acting.world.uow, acting.world.clock, FakeIdFactory())
    return (await started.execute(CTX)).id


async def test_an_enabled_tenant_is_answered_by_the_brain() -> None:
    acting = await _acting()
    asker = FakeAsker(_call("check_mail"), _say("Nothing new that asks for a job."))
    converse = _converse(acting, asker, on=(TENANT,))

    thread = await converse.execute(
        CTX, thread_id=await _thread(acting), text="check mail for any new work"
    )

    assert [(m.speaker.value, m.text) for m in thread.messages] == [
        ("operator", "check mail for any new work"),
        ("assistant", "Nothing new that asks for a job."),
    ]
    assert len(asker.asked) == 2 and "check_mail" in str(asker.asked[1])
    assert acting.started == []


async def test_a_run_the_brain_started_is_the_decision_the_panel_watches() -> None:
    acting = await _acting()
    asker = FakeAsker(_call("start_job", job_id=JOB, values=GIVEN), _say("Started it."))
    converse = _converse(acting, asker, on=(TENANT,))
    thread_id = await _thread(acting)

    thread = await converse.execute(
        CTX, thread_id=thread_id, text="create customer type SR11 with the description new"
    )

    (run_id,) = acting.started
    assert thread.messages[-1].decision == {"kind": "run", "run_id": run_id}
    run = await acting.world.uow.workflow_runs.get(f.TENANT, run_id)
    assert run is not None and (run.offer or "").startswith(f"chat:{thread.messages[0].id.value}:")
    rows = acting.world.uow.attempts.rows
    assert [(one.came_of, one.about["run"]) for one in rows] == [(DONE, run_id)]


class _Scripted:
    """The brain port, scripted: a turn that started two runs and then asked."""

    def __init__(self, reply: BrainReply) -> None:
        self._reply = reply

    async def turn(self, *_: object, **__: object) -> BrainReply:
        return self._reply


async def test_every_run_a_turn_started_keeps_its_card_and_the_question_follows() -> None:
    acting = await _acting()
    converse = _converse(acting, FakeAsker(), on=(TENANT,))
    start = ToolCall("start_job", {})
    one = ToolResult(True, ends_turn=False, decision={"kind": "run", "run_id": "run_a"}, said="A.")
    two = ToolResult(True, ends_turn=False, decision={"kind": "run", "run_id": "run_b"}, said="B.")
    ask = ToolResult(True, decision={"kind": "brain_asks", "question": "Which department?"})
    converse._brain = _Scripted(  # type: ignore[assignment]
        BrainReply(
            "Which department?",
            (one.decision or {}, two.decision or {}, ask.decision or {}),
            ((start, one), (start, two), (ToolCall("ask_operator", {}), ask)),
        )
    )

    thread = await converse.execute(CTX, thread_id=await _thread(acting), text="make two")

    assert [(m.speaker.value, (m.decision or {}).get("kind")) for m in thread.messages] == [
        ("operator", None),
        ("assistant", "run"),
        ("assistant", "run"),
        ("assistant", "brain_asks"),
    ]
    assert [(m.decision or {}).get("run_id") for m in thread.messages[1:3]] == ["run_a", "run_b"]
    assert thread.messages[-1].text == "Which department?"


async def test_only_a_question_is_handed_to_the_brain_as_the_open_question() -> None:
    acting = await _acting()
    asker = FakeAsker(
        _call("start_job", job_id=JOB, values=GIVEN),
        _call("ask_operator", question="Which department?"),
        _say("Noted."),
    )
    converse = _converse(acting, asker, on=(TENANT,))
    thread_id = await _thread(acting)

    await converse.execute(
        CTX, thread_id=thread_id, text="create customer type SR11 with the description new"
    )
    await converse.execute(CTX, thread_id=thread_id, text="which department can I use?")
    await converse.execute(CTX, thread_id=thread_id, text="Returns")

    assert 'name="asking"' not in str(asker.asked[1]["evidence"])
    assert '<untrusted name="asking">\nWhich department?' in str(asker.asked[2]["evidence"])


async def test_a_run_the_brain_took_back_is_recorded_as_an_attempt() -> None:
    acting = await _acting()
    converse = _converse(acting, FakeAsker(), on=(TENANT,))
    done = ToolResult(
        True,
        {"run_id": "run_undo"},
        decision={"kind": "run", "run_id": "run_undo"},
        said="Started it.",
    )
    refused = ToolResult(False, error="already taken back")
    converse._brain = _Scripted(  # type: ignore[assignment]
        BrainReply(
            "ok",
            (done.decision or {},),
            (
                (ToolCall("undo_run", {"run_id": "run_a"}), done),
                (ToolCall("undo_run", {"run_id": "run_b"}), refused),
            ),
        )
    )

    await converse.execute(CTX, thread_id=await _thread(acting), text="undo that")

    rows = acting.world.uow.attempts.rows
    assert [(r.asked_for, r.came_of, r.about.get("run", "")) for r in rows] == [
        ("take back a run", DONE, "run_undo"),
        ("take back a run", REFUSED, ""),
    ]


async def test_a_question_of_the_brain_is_an_ordinary_question_message() -> None:
    acting = await _acting()
    asker = FakeAsker(_call("ask_operator", question="Which customer type?"))
    converse = _converse(acting, asker, on=(TENANT,))

    thread = await converse.execute(CTX, thread_id=await _thread(acting), text="make a type")

    last = thread.messages[-1]
    assert last.text == "Which customer type?"
    assert last.decision == {"kind": "brain_asks", "question": "Which customer type?"}


async def test_a_yes_to_an_open_offer_never_asks_the_brain() -> None:
    acting = await _acting()
    asker = FakeAsker()
    thread_id = await _thread(acting)
    offered = await _converse(acting, asker).execute(
        CTX, thread_id=thread_id, text="create customer type SR11"
    )
    offer = offered.messages[-1]
    assert (offer.decision or {}).get("kind") == "job"

    said = await _converse(acting, asker, on=(TENANT,)).execute(
        CTX, thread_id=thread_id, text="yes", answering=offer.id.value
    )

    assert asker.asked == []
    assert len(acting.started) == 1
    assert (said.messages[-1].decision or {}).get("run_id") == acting.started[0]


async def test_a_tenant_that_is_not_listed_gets_the_old_chain_and_the_brain_is_not_asked() -> None:
    acting = await _acting()
    asker = FakeAsker()
    converse = _converse(acting, asker, on=("another-tenant",), shadow=("a-third",))

    thread = await converse.execute(
        CTX, thread_id=await _thread(acting), text="create customer type SR11"
    )

    assert (thread.messages[-1].decision or {}).get("kind") == "job"
    assert asker.asked == [] and acting.spawned == []


async def test_a_shadow_tenant_gets_the_old_answer_and_the_brain_only_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    acting = await _acting()
    asker = FakeAsker(_call("start_job", job_id=JOB, values=GIVEN), _say("Started it."))
    converse = _converse(acting, asker, shadow=(TENANT,))
    caplog.set_level(logging.INFO, logger="sro.application.chat.brain")

    thread = await converse.execute(
        CTX, thread_id=await _thread(acting), text="create customer type SR11"
    )
    for later in list(acting.spawned):
        await later

    assert (thread.messages[-1].decision or {}).get("kind") == "job"
    assert acting.started == [] and asker.asked
    (line,) = [r.getMessage() for r in caplog.records if r.getMessage().startswith("brain shadow")]
    job = await acting.world.uow.workflows.get(f.TENANT, JOB)
    assert job is not None
    assert "start_job" in line and job.title in line and "Started it." in line
    assert "SR11" not in line


async def test_a_brain_that_fails_live_answers_plainly_after_the_message_is_saved() -> None:
    class _Down(FakeAsker):
        async def ask(self, **kwargs: Any) -> Any:
            raise RuntimeError("connect to 10.11.9.25:5432 refused")

    acting = await _acting()
    converse = _converse(acting, _Down(), on=(TENANT,))

    thread = await converse.execute(CTX, thread_id=await _thread(acting), text="check mail")

    assert [(m.speaker.value, m.text) for m in thread.messages] == [
        ("operator", "check mail"),
        ("assistant", "I can't answer right now: something went wrong."),
    ]


async def test_a_brain_that_fails_in_shadow_never_touches_the_answer(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class _Down(FakeAsker):
        async def ask(self, **kwargs: Any) -> Any:
            raise RuntimeError("the model fell over")

    acting = await _acting()
    converse = _converse(acting, _Down(), shadow=(TENANT,))

    thread = await converse.execute(
        CTX, thread_id=await _thread(acting), text="create customer type SR11"
    )
    for later in list(acting.spawned):
        await later

    assert (thread.messages[-1].decision or {}).get("kind") == "job"
    assert any("brain turn failed" in r.getMessage() for r in caplog.records)


def test_the_flags_are_read_from_the_environment_like_steel_tenants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert Settings().chat_brain_tenants == () == Settings().chat_brain_shadow_tenants
    monkeypatch.setenv("SRO_CHAT_BRAIN_TENANTS", '["greyorange"]')
    monkeypatch.setenv("SRO_CHAT_BRAIN_SHADOW_TENANTS", '["a","b"]')

    settings = Settings()

    assert settings.chat_brain_tenants == ("greyorange",)
    assert settings.chat_brain_shadow_tenants == ("a", "b")
