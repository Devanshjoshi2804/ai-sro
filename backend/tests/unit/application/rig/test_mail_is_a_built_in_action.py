"""Send, reply and forward are built-in mail actions, never learned jobs.

Decided with the user 2026-09-28: mail work runs on the Gmail connector only.
The user's own test on runtime-9ee015a -- a chat yes to `Compose and Send
Email`, drafted from their words, Send pressed, sent by the Gmail tool -- is
the path. A built-in action runs that same path with the same guards; it only
takes the mined job's place, so a tenant with no mined mail job is served too.

Held here, through the real reader, the real start and the real send (Q1, 2026-09-28:
the mail goes as soon as it is written; there is no Send to press):
- "send an email to ..." reaches the built-in even with no job mined;
- a mail-only mined job is no candidate, and its demonstrated recipients are
  the built-in's;
- reply and forward act on the chat's mail, or on one the operator names --
  asked in the panel, never guessed;
- a mail action never goes to Steel.
"""

from __future__ import annotations

import json
from collections.abc import Coroutine, Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

from sro.application.chat.converse import Converse, StartThread
from sro.application.chat.mailbox import SERVER
from sro.application.chat.read_chat import ReadChat
from sro.application.context import RequestContext
from sro.application.execution.approvals import Approvals
from sro.application.execution.gather import GatherContext
from sro.application.execution.one_time_secrets import OneTimeSecrets
from sro.application.execution.stops import Stops
from sro.application.execution.workflow_runs import StartWorkflowRun
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.application.ports.tools import ToolResult
from sro.application.runtime.answer_run import AnswerRun
from sro.domain.execution.mail_job import (
    FORWARD_A_MAIL,
    REPLY_TO_A_MAIL,
    SEND_A_MAIL,
    WHICH_MAIL,
)
from sro.domain.execution.progress import Progress
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.gesture import Action, Body, Call, Gesture, Target
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from tests import factories as f
from tests.unit.fakes import (
    FakeAsker,
    FakeChannel,
    FakeClock,
    FakeDurableExecution,
    FakeEmbedder,
    FakeIdFactory,
    FakeUnitOfWork,
)

A = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("devansh"))
B = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("colleague"))
GMAIL = "https://mail.google.com/mail/u/0/#inbox"
TO = "devansh.j@greyorange.com"
REQUEST = f'send an email to "{TO}" say Hi in subject and body. THis is a test email.'
ALEX = "alex.r@example.com"
ASKED = [
    {
        "id": "m-1",
        "from": f"Alex R <{ALEX}>",
        "to": "devansh@wh.example",
        "subject": "New customer type",
        "rfc822_message_id": "<req@mail>",
        "body": "Please set up customer type NRT2 for the pilot.",
    }
]
SENT_THREAD = 1845678901234567890


def _read(job: str) -> Answer:
    return Answer(data={"job": job, "sure": True, "values": []}, cost_usd=0.001)


def _wrote(to: str = TO, body: str = "Hi\n\nThis is a test email.") -> Answer:
    return Answer(
        data={
            "to": to,
            "subject": "Hi",
            "body": body,
            "cited": [
                {"value": "Hi", "message": "request"},
                {"value": "This is a test email", "message": "request"},
            ],
        },
        cost_usd=0.001,
    )


class _Mailbox:
    """The operator's mailbox: conversations, a search, and every send."""

    def __init__(self, **threads: list[dict[str, object]]) -> None:
        self.sent: list[dict[str, str]] = []
        self.threads = threads
        self.searched: list[str] = []

    @property
    def available(self) -> bool:
        return True

    async def list_tools(self, tenant_id: TenantId, principal_id: PrincipalId, server: str) -> Any:
        return ()

    async def call(
        self,
        tenant_id: TenantId,
        principal_id: PrincipalId,
        server: str,
        tool: str,
        arguments: Mapping[str, str],
    ) -> ToolResult:
        if tool == "send_message":
            self.sent.append(dict(arguments))
            return ToolResult(text=json.dumps({"id": f"gm-{len(self.sent)}"}))
        if tool == "get_thread" and arguments.get("id") in self.threads:
            return ToolResult(text=json.dumps({"messages": self.threads[arguments["id"]]}))
        if tool == "search_threads":
            self.searched.append(arguments["query"])
            words = arguments["query"].casefold().split()
            found = [
                {"id": one["id"]}
                for messages in self.threads.values()
                for one in messages
                if all(word in json.dumps(one).casefold() for word in words)
            ]
            return ToolResult(text=json.dumps({"messages": found, "next_page": ""}))
        if tool == "get_message":
            thread = next(
                (
                    name
                    for name, messages in self.threads.items()
                    for one in messages
                    if one["id"] == arguments["id"]
                ),
                "",
            )
            return ToolResult(text=json.dumps({"id": arguments["id"], "thread_id": thread}))
        return ToolResult(text="no such conversation", failed=True)


class _World:
    def __init__(self, *answers: Answer, mailbox: _Mailbox | None = None) -> None:
        self.uow = FakeUnitOfWork()
        self.ids = FakeIdFactory()
        self.clock = FakeClock(datetime.now(tz=UTC))
        self.mailbox = mailbox or _Mailbox()
        self.asker = FakeAsker(*answers)
        self.durable = FakeDurableExecution()
        self.spawned: list[Coroutine[object, object, None]] = []
        self.starter = StartWorkflowRun(
            self.uow,
            channel=FakeChannel(),
            asker=self.asker,
            clock=self.clock,
            cap_usd=100.0,
            stops=Stops(),
            approvals=Approvals(),
            one_time_secrets=OneTimeSecrets(),
            gather=GatherContext(tools=self.mailbox, asker=self.asker),
            ids=self.ids,
            durable=self.durable,
            steel_tenants=frozenset({f.TENANT.value}),
        )
        self.converse = Converse(
            self.uow,
            ResolveIntent(self.uow, PlanTask(Retrieve(self.uow, FakeEmbedder()))),
            self.clock,
            self.ids,
            reads_jobs=ReadChat(self.uow, asker=self.asker, clock=self.clock, cap_usd=100.0),
            answer_run=AnswerRun(self.uow, self.durable, resume=self.starter.answered),
            start=self.starter,
            spawn=self.spawned.append,
        )

    async def ask_and_say_yes(self, text: str = REQUEST) -> WorkflowRun:
        thread = await StartThread(self.uow, self.clock, self.ids).execute(A)
        offered = await self.converse.execute(A, thread_id=thread.id, text=text)
        decision = dict(offered.messages[-1].decision or {})
        assert decision.get("kind") == "job", offered.messages[-1].text
        said = await self.converse.execute(A, thread_id=thread.id, text="Yes")
        started = dict(said.messages[-1].decision or {})
        assert started.get("resume") is True, said.messages[-1].text
        for performing in self.spawned:
            await performing
        self.spawned.clear()
        return await self.saved(str(started["run_id"]))

    async def saved(self, run_id: str) -> WorkflowRun:
        run = await self.uow.workflow_runs.get(f.TENANT, run_id)
        assert run is not None
        return run

    def candidates(self) -> list[str]:
        evidence = str(self.asker.asked[0]["evidence"])
        fence = evidence.split('<untrusted name="candidates">\n', 1)[1]
        return [one["id"] for one in json.loads(fence.split("\n</untrusted>", 1)[0])]

    async def decisions(self) -> list[dict[str, Any]]:
        (thread,) = await self.uow.threads.list_for_tenant(
            f.TENANT, opened_by=A.principal_id, limit=1
        )
        return [dict(one.decision or {}) for one in thread.messages]

    async def answer(self, who: RequestContext, run: WorkflowRun, value: str) -> None:
        asking = Progress.of(run.progress).asking
        await AnswerRun(self.uow, self.durable, resume=self.starter.answered).execute(
            who, run_id=run.id, question_id=asking["id"], value=value
        )


# --- send: the user's test, with no mined job at all --------------------------


async def test_a_tenant_with_no_mail_job_sends_through_the_built_in_action() -> None:
    world = _World(_read(SEND_A_MAIL), _wrote())

    run = await world.ask_and_say_yes()

    assert SEND_A_MAIL in world.candidates()
    assert run.workflow_id == SEND_A_MAIL
    assert run.executor != "steel", "a mail action never goes to Steel"
    assert world.durable.runs_started == []
    (sent,) = world.mailbox.sent
    assert (sent["to"], sent["subject"], sent["thread_id"]) == (TO, "Hi", ""), "sent at once"
    assert sent["marker"], "X-SRO-Marker rides every send"
    assert run.outcome == "held"
    kept = await world.uow.workflows.recipients_for(f.TENANT, SEND_A_MAIL)
    assert [one.address for one in kept] == [TO], "kept once it went, on the built-in"


async def test_a_send_to_somebody_the_operator_never_named_is_asked_about() -> None:
    world = _World(_read(SEND_A_MAIL), _wrote(to="eve@evil.example"))

    run = await world.ask_and_say_yes()

    assert Progress.of(run.progress).asking["kind"] == "recipient"
    assert world.mailbox.sent == []


# --- a mail-only mined job is no candidate; its evidence is the built-in's -----


def _pressed_send() -> Gesture:
    return Gesture(
        id="g-send",
        tenant=f.TENANT.value,
        stream_id="str-1",
        batch_id="bat-1",
        at=1_000.0,
        url=GMAIL,
        system=GMAIL,
        tab_id=7,
        frame_url=None,
        action=Action(
            kind="click",
            at=1_000.0,
            url=GMAIL,
            target=Target(tag="div", role="button", name="Send ‪(⌘Enter)‬"),
        ),
        requests=[
            Call(
                method="POST",
                url="https://mail.google.com/sync/u/0/i/s?hl=en&c=51",
                status=200,
                response_body=Body(text=f'[["thread-f:{SENT_THREAD}",[["msg-f:1"]]]]'),
            )
        ],
    )


async def test_the_mined_mail_job_is_no_candidate_and_its_recipients_are_the_built_in_s() -> None:
    vendor = "vendor@supplier.example"
    sent = {"id": "s-1", "sent": True, "sent_at": 1_003.0, "to": vendor}
    mailbox = _Mailbox(**{format(SENT_THREAD, "x"): [sent]})
    world = _World(
        _read(SEND_A_MAIL),
        _wrote(to=vendor, body="Hi\n\nThis is a test email."),
        mailbox=mailbox,
    )
    await world.uow.gestures.add_gestures((_pressed_send(),))
    await world.uow.workflows.save(
        Workflow(
            id="wfl_compose",
            tenant=f.TENANT.value,
            title="Compose and Send Email",
            narrative="the operator wrote a new mail and sent it",
            steps=[Step(order=0, says="Write it and press Send", system=None, cites=["g-send"])],
        )
    )

    await world.ask_and_say_yes("send the vendor a test email saying Hi")

    assert "wfl_compose" not in world.candidates()
    (went,) = world.mailbox.sent
    assert went["to"] == vendor, "the address the mined job was shown sending to"


# --- reply and forward act on a mail --------------------------------------------


async def test_a_reply_started_on_a_mail_answers_that_mail() -> None:
    """Every door starts a run with the conversation it came from; a reply
    started on one needs no question about which mail."""
    world = _World(
        Answer(
            data={
                "to": ALEX,
                "subject": "Re: New customer type",
                "body": "Hi, customer type NRT2 is set up.",
                "cited": [{"value": "NRT2", "message": "m-1"}],
            },
            cost_usd=0.001,
        ),
        mailbox=_Mailbox(**{"t-alex": ASKED}),
    )
    run = await world.starter.execute(
        A,
        workflow_id=REPLY_TO_A_MAIL,
        device_id=None,
        values={},
        live=True,
        allow_focus=True,
        conversation=(SERVER, "t-alex"),
    )
    assert run.executor != "steel"
    await world.starter.perform(A, run)

    (sent,) = world.mailbox.sent
    assert (sent["to"], sent["thread_id"]) == (ALEX, "t-alex")
    assert sent["in_reply_to"] == "<req@mail>"


@pytest.mark.parametrize("action", [REPLY_TO_A_MAIL, FORWARD_A_MAIL])
async def test_a_reply_or_forward_with_no_mail_asks_which_and_drafts_on_the_one_found(
    action: str,
) -> None:
    world = _World(
        _read(action),
        _wrote(to=ALEX, body="Hi\n\nThis is a test email."),
        mailbox=_Mailbox(**{"t-alex": ASKED, "t-other": [{"id": "m-2", "subject": "Lunch"}]}),
    )

    run = await world.ask_and_say_yes("answer Alex: Hi, this is a test email")

    asking = Progress.of(run.progress).asking
    assert asking["kind"] == WHICH_MAIL
    assert len(world.asker.asked) == 1, "nothing is written before the mail is known"
    asks = [one for one in await world.decisions() if one.get("kind") == "run_asks"]
    assert [one["asks"] for one in asks] == [WHICH_MAIL]

    await world.answer(A, run, "NRT2 pilot")

    assert world.mailbox.searched == ["NRT2 pilot"]
    (sent,) = world.mailbox.sent
    assert (sent["thread_id"], sent["in_reply_to"]) == ("t-alex", "<req@mail>")


@pytest.mark.parametrize(("words", "found"), [("invoice", 0), ("NRT2", 2)])
async def test_words_that_find_no_mail_or_several_ask_again(words: str, found: int) -> None:
    mailbox = _Mailbox(**{"t-alex": ASKED, "t-other": [{"id": "m-2", "subject": "NRT2 lunch"}]})
    world = _World(_read(REPLY_TO_A_MAIL), mailbox=mailbox)
    run = await world.ask_and_say_yes("reply to the mail")

    await world.answer(A, run, words)

    again = await world.saved(run.id)
    asking = Progress.of(again.progress).asking
    assert asking["kind"] == WHICH_MAIL and f"{found} mail" in asking["text"]
    assert world.mailbox.sent == [] and len(world.asker.asked) == 1


async def test_only_the_starter_names_the_mail_and_only_once() -> None:
    world = _World(
        _read(REPLY_TO_A_MAIL),
        _wrote(to=ALEX, body="Hi\n\nThis is a test email."),
        _wrote(to=ALEX, body="Hi\n\nThis is a test email."),
        mailbox=_Mailbox(**{"t-alex": ASKED}),
    )
    run = await world.ask_and_say_yes("reply to the mail: Hi, this is a test email")

    with pytest.raises(Conflict):
        await world.answer(B, run, "NRT2")
    await world.answer(A, run, "NRT2")
    with pytest.raises(Conflict):
        await world.answer(A, run, "something else")
    await world.starter.answered(A, run.id)

    assert len(world.mailbox.sent) == 1
