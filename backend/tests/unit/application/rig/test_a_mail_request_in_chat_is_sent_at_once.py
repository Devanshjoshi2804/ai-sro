"""A mail request in chat is written and sent, like Slackbot does it (Q1).

QA thread thr_d13d, 2026-09-28: a stray run's "who does this mail go to?" was
still open when the operator asked for a new mail. The request was taken as
that question's answer, refused, and dropped; "to devansh.j@..." was refused
too; only a bare address was taken, and it mailed the stray run's old draft.

Held here through the real chat path -- `Converse` with the real reader, the
real start, the real answer and the real mail job; fakes only at the ports:
- a new request under an open run question is carried on as a new request, and
  the old question is asked again, never answered by it;
- a mail is sent as soon as it is written -- there is no Send to press -- and
  the thread shows what went;
- "to <address>" answers who a mail goes to;
- a plain answer still reaches the run.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from sro.application.chat.converse import Converse, StartThread
from sro.application.chat.read_chat import ReadChat
from sro.application.chat.reading_an_answer import IsItAnAnswer
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.application.runtime.answer_run import AnswerRun
from sro.domain.chat.thread import Thread
from sro.domain.execution.mail_job import SEND_A_MAIL
from sro.domain.execution.progress import Progress
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.shared.prices import Answer
from tests import factories as f
from tests.unit.application.rig.test_mail_is_a_built_in_action import (
    TO,
    A,
    _read,
    _World,
    _wrote,
)
from tests.unit.fakes import FakeEmbedder
from tests.unit.runtime_support import save_job

STRAY = "send a mail to somebody saying Hi"
ASKED_FOR = (
    f"write a mail to ask {TO} and draft a mail to ask needed to update warehouse "
    "inventory need status for 28 sep"
)
STRANGER = "eve@evil.example"
LEARNED = "wfl_1"


def _not_an_answer(about: str) -> Answer:
    return Answer(
        data={"answers": False, "value": "", "why": "not who it goes to", "about": about},
        cost_usd=0.001,
    )


def _an_answer() -> Answer:
    return Answer(
        data={"answers": True, "value": "", "why": "names who", "about": "something_else"},
        cost_usd=0.001,
    )


def _warehouse() -> Answer:
    return Answer(
        data={
            "to": TO,
            "subject": "Warehouse inventory update status for 28 Sep",
            "body": "Hi,\n\nWhat is the status of the warehouse inventory update for 28 Sep?",
            "cited": [{"value": "28 sep", "message": "request"}],
        },
        cost_usd=0.001,
    )


class _Chat(_World):
    """The container's chat: `Converse` reads an answer with the model too."""

    def __init__(self, *answers: Answer) -> None:
        super().__init__(*answers)
        self.converse = Converse(
            self.uow,
            ResolveIntent(self.uow, PlanTask(Retrieve(self.uow, FakeEmbedder()))),
            self.clock,
            self.ids,
            reads_jobs=ReadChat(self.uow, asker=self.asker, clock=self.clock, cap_usd=100.0),
            answers=IsItAnAnswer(self.asker),
            answer_run=AnswerRun(self.uow, self.durable, resume=self.starter.answered),
            start=self.starter,
            spawn=self.spawned.append,
        )

    async def thread(self) -> Thread:
        (thread,) = await self.uow.threads.list_for_tenant(
            f.TENANT, opened_by=A.principal_id, limit=1
        )
        return thread

    async def say(self, text: str, *, answering: str | None = None) -> Thread:
        said = await self.converse.execute(
            A, thread_id=(await self.thread()).id, text=text, answering=answering
        )
        for performing in self.spawned:
            await performing
        self.spawned.clear()
        return said

    async def a_stray_question(self) -> WorkflowRun:
        await StartThread(self.uow, self.clock, self.ids).execute(A)
        said = await self.say(STRAY)
        run = await self.saved(_started(said))
        assert Progress.of(run.progress).asking["kind"] == "recipient"
        return run

    def written_for(self) -> list[str]:
        return [
            str(one["evidence"])
            for one in self.asker.asked
            if '"to"' in json.dumps(one.get("schema", {}))
        ]


def _started(thread: Thread) -> str:
    """The run a request started at once: no offer, no yes."""
    (started,) = [one for one in thread.messages if (one.decision or {}).get("resume")][-1:]
    return str((started.decision or {})["run_id"])


def _kinds(thread: Thread) -> list[Any]:
    return [(one.decision or {}).get("kind") for one in thread.messages]


async def test_a_new_mail_request_under_an_open_run_question_is_written_and_sent() -> None:
    world = _Chat(
        _read(SEND_A_MAIL),
        _wrote(to=STRANGER),
        _not_an_answer("another_task"),
        _read(SEND_A_MAIL),
        _warehouse(),
    )
    stray = await world.a_stray_question()

    said = await world.say(ASKED_FOR)

    assert not [one for one in said.messages if "say the word" in one.text], "no offer, no yes"
    request = next(n for n, one in enumerate(said.messages) if one.text == ASKED_FOR)
    asked_again = said.messages[request - 1]
    assert (asked_again.decision or {}).get("kind") == "run_asks", "asked again, first"
    assert (asked_again.decision or {})["run_id"] == stray.id
    after = [(one.decision or {}).get("kind") for one in said.messages[request:]]
    assert "run_asks" not in after, "the new request's messages are the latest"
    run = await world.saved(_started(said))
    assert run.id != stray.id and run.workflow_id == SEND_A_MAIL
    assert ASKED_FOR in world.written_for()[-1], "WRITE_MAIL was given the request"
    (sent,) = world.mailbox.sent
    assert sent["to"] == TO, "sent at once -- nothing to press"
    assert run.outcome == "held"
    shown = (await world.thread()).messages[-1]
    assert f"Sent to {TO}" in shown.text
    assert "Warehouse inventory update status for 28 Sep" in shown.text
    assert "What is the status of the warehouse inventory update for 28 Sep?" in shown.text
    old = await world.saved(stray.id)
    assert not Progress.of(old.progress).asking.get("answered"), "the old question stands"
    assert old.outcome == "stopped"


async def test_a_typed_yes_after_a_new_task_under_a_run_question_starts_the_new_task() -> None:
    """The old question is asked again first, so the offer is the latest thing
    said, and a typed yes -- no `answering` -- is the offer's."""
    world = _Chat(
        _read(SEND_A_MAIL),
        _wrote(to=STRANGER),
        _not_an_answer("another_task"),
        _read(LEARNED),
    )
    stray = await world.a_stray_question()
    await world.uow.workflows.save(replace(await save_job(world.uow, LEARNED), parameters=[]))

    offered = await world.say("set up the customer type")
    assert (offered.messages[-1].decision or {}).get("kind") == "job", "the offer is last"
    said = await world.say("yes")

    started = said.messages[-1].decision or {}
    assert started.get("resume") is True, said.messages[-1].text
    assert started["workflow_id"] == LEARNED
    old = await world.saved(stray.id)
    assert not Progress.of(old.progress).asking.get("answered"), "the old question stands"


async def test_to_an_address_answers_who_a_mail_goes_to() -> None:
    world = _Chat(_read(SEND_A_MAIL), _wrote(to=STRANGER), _an_answer(), _wrote(to=TO))
    stray = await world.a_stray_question()

    await world.say(f"to {TO}")

    old = await world.saved(stray.id)
    assert Progress.of(old.progress).asking == {}, "answered, and the mail rewritten"
    (sent,) = world.mailbox.sent
    assert sent["to"] == TO
    assert old.outcome == "held"


async def test_a_plain_answer_still_reaches_the_run() -> None:
    world = _Chat(_read(SEND_A_MAIL), _wrote(to=STRANGER), _wrote(to=TO))
    stray = await world.a_stray_question()

    await world.say(TO)

    assert len(world.asker.asked) == 3, "a bare address is plainly the answer; no model read"
    (sent,) = world.mailbox.sent
    assert sent["to"] == TO
    assert (await world.saved(stray.id)).outcome == "held"


async def test_small_talk_under_a_run_question_asks_it_again() -> None:
    world = _Chat(_read(SEND_A_MAIL), _wrote(to=STRANGER), _not_an_answer("something_else"))
    stray = await world.a_stray_question()

    thread = await world.say("hmm, let me think about who")

    assert _kinds(thread)[-2:] == [None, "run_asks"], "noted, then asked again"
    assert thread.messages[-1].text == thread.messages[-3].text
    assert world.mailbox.sent == []
    assert not Progress.of((await world.saved(stray.id)).progress).asking.get("answered")


async def test_a_mail_request_that_cannot_start_says_so_once_under_the_request() -> None:
    """The request is said once; the refusal answers it -- no second copy of
    the operator's words, no offer left behind to say yes to."""
    world = _Chat(_read(SEND_A_MAIL))
    world.converse._start = None
    await StartThread(world.uow, world.clock, world.ids).execute(A)

    said = await world.say(ASKED_FOR)

    assert [one.text for one in said.messages] == [
        ASKED_FOR,
        "Nothing was started: this process cannot start a run.",
    ]
    assert world.mailbox.sent == []
