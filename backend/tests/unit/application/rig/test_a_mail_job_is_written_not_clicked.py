"""A job that is nothing but mail is written through the mailbox, not clicked.

Measured on the deployment 2026-09-23: three runs of `Reply to Email` refused
with "a click cannot carry a value" -- one mined step carried the recipients,
the subject and the body -- and three of `Compose and Send Email` ended "state
unknown after a write", because nothing on a screen can say a mail went.

What is held here is the shape of the replacement: a model writes the mail
from the job and the conversation it answers, it is put in front of the
operator and nothing is sent, their press sends exactly those words into the
right conversation, and Gmail's answer finishes the run.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sro.application.chat.ask_the_asker import DRAFTED, SendTheDraft
from sro.application.context import RequestContext
from sro.application.execution.mail_job import draft_the_mail_job
from sro.application.ports.tools import ToolResult
from sro.domain.execution.mail_job import is_mail_only, recipient_allowed
from sro.domain.execution.waiting import as_said, waiting_on
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.gesture import Action, Gesture, Target
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from tests import factories as f
from tests.unit.fakes import FakeAsker, FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("devansh"))
THREAD = "t-reply"
GMAIL = "https://mail.google.com/mail/u/0/#inbox"


class _Mailbox:
    """A connector holding one conversation, and every send it was asked for."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

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
            return ToolResult(text=json.dumps({"status": "sent", "id": "gm-42"}))
        return ToolResult(
            text=json.dumps(
                {
                    "id": THREAD,
                    "messages": [
                        {
                            "id": "m-1",
                            "from": "Alex R <alex.r@example.com>",
                            "subject": "New customer type",
                            "rfc822_message_id": "<req@mail>",
                            "body": "Please set up customer type NRT2 for the pilot.",
                        }
                    ],
                }
            )
        )


def _gesture(gesture_id: str, url: str) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant=f.TENANT.value,
        stream_id="str-1",
        batch_id="bat-1",
        at=1_000.0,
        url=url,
        system=url,
        tab_id=7,
        frame_url=None,
        action=Action(kind="click", at=1_000.0, url=url, target=Target(tag="button"), value=None),
    )


def _reply_job() -> Workflow:
    return Workflow(
        id="wfl_reply",
        tenant=f.TENANT.value,
        title="Reply to Email",
        narrative="the operator answered the mail that asked for a customer type",
        steps=[
            Step(order=0, says="Open the email thread", system=None, cites=["g-open"]),
            Step(order=1, says="Click Reply, write it, Send", system=None, cites=["g-send"]),
        ],
    )


async def _a_run(uow: FakeUnitOfWork, *, thread: str = THREAD) -> WorkflowRun:
    run = WorkflowRun(
        id="run_mail",
        tenant=f.TENANT.value,
        workflow_id="wfl_reply",
        device_id="dev-1",
        values={"Customer Type": "NRT2"},
        started_by="devansh",
        live=True,
        allow_focus=True,
        started_at=datetime.now(tz=UTC).isoformat(),
        outcome="running",
        awaiting=as_said(waiting_on("gmail", thread, now=datetime.now(tz=UTC))) if thread else None,
    )
    await uow.workflow_runs.save(run)
    return run


def _written(to: str) -> FakeAsker:
    return FakeAsker(
        Answer(
            data={
                "to": to,
                "subject": "Re: New customer type",
                "body": "Customer type NRT2 is set up.\n\ndevansh",
            },
            cost_usd=0.001,
        )
    )


def test_only_a_job_that_is_all_mailbox_is_a_mail_job() -> None:
    """A job with one step anywhere else is a page that has to be driven, and
    its mail half is read by the gather rung as it always was."""
    by_id = {
        "g-open": _gesture("g-open", GMAIL),
        "g-send": _gesture("g-send", GMAIL),
        "g-wms": _gesture("g-wms", "https://wms.example/portal"),
    }
    assert is_mail_only(_reply_job(), by_id)

    mixed = _reply_job()
    mixed.steps.append(Step(order=2, says="Save it in the WMS", system=None, cites=["g-wms"]))
    assert not is_mail_only(mixed, by_id)


def test_a_recipient_is_copied_never_invented() -> None:
    known = frozenset({"alex.r@example.com"})
    assert recipient_allowed("alex.r@example.com", known)
    assert recipient_allowed("Alex R <ALEX.R@example.com>", known)
    assert not recipient_allowed("someone.else@example.com", known)
    assert not recipient_allowed("alex.r@example.com, stranger@example.com", known)
    assert not recipient_allowed("", known)


async def test_the_mail_is_written_and_put_in_front_of_the_operator_unsent() -> None:
    uow, mailbox = FakeUnitOfWork(), _Mailbox()
    run = await _a_run(uow)

    done = await draft_the_mail_job(
        CTX,
        run,
        _reply_job(),
        uow=uow,
        tools=mailbox,
        asker=_written("alex.r@example.com"),
        clock=FakeClock(),
        ids=FakeIdFactory(),
    )

    assert mailbox.sent == [], "a mail went out before anybody read it"
    threads = await uow.threads.list_for_tenant(f.TENANT, opened_by=PrincipalId("devansh"), limit=1)
    drafted = threads[0].messages[-1].decision
    assert drafted["kind"] == DRAFTED
    assert drafted["job"] == "wfl_reply"
    assert drafted["to"] == "alex.r@example.com"
    # Inside the conversation it answers, as a reply to the request itself.
    assert drafted["thread"] == THREAD
    assert drafted["in_reply_to"] == "<req@mail>"
    # Parked on the press, and not holding the browser while it waits.
    assert done.outcome == "stopped"
    assert [step.verdict for step in done.steps] == ["awaiting"]


async def test_a_mail_to_somebody_nobody_named_is_never_drafted() -> None:
    """The one step of this job that cannot be taken back is who it goes to."""
    uow, mailbox = FakeUnitOfWork(), _Mailbox()
    run = await _a_run(uow)

    done = await draft_the_mail_job(
        CTX,
        run,
        _reply_job(),
        uow=uow,
        tools=mailbox,
        asker=_written("stranger@example.com"),
        clock=FakeClock(),
        ids=FakeIdFactory(),
    )

    assert mailbox.sent == []
    assert done.outcome == "stopped"
    assert done.steps[-1].verdict == "failed"
    assert "names nobody this job was given" in done.steps[-1].reason


async def test_the_press_sends_it_and_gmails_answer_finishes_the_run() -> None:
    uow, mailbox = FakeUnitOfWork(), _Mailbox()
    run = await _a_run(uow)
    await draft_the_mail_job(
        CTX,
        run,
        _reply_job(),
        uow=uow,
        tools=mailbox,
        asker=_written("alex.r@example.com"),
        clock=FakeClock(),
        ids=FakeIdFactory(),
    )
    threads = await uow.threads.list_for_tenant(f.TENANT, opened_by=PrincipalId("devansh"), limit=1)
    drafted = threads[0].messages[-1]

    to = await SendTheDraft(uow, mailbox, FakeClock(), FakeIdFactory()).execute(
        CTX, threads[0].id, drafted.id
    )

    assert to == "alex.r@example.com"
    (sent,) = mailbox.sent
    assert sent["body"] == drafted.decision["body"], "the words sent were not the words read"
    assert sent["thread_id"] == THREAD
    assert sent["in_reply_to"] == "<req@mail>"

    finished = await uow.workflow_runs.get(f.TENANT, "run_mail")
    assert finished is not None
    assert finished.outcome == "held"
    (step,) = finished.steps
    assert (step.verdict, step.verdict_by) == ("held", "status")
    assert step.made == {"message": "gm-42"}
    # A finished job is not waiting to hear back from anybody.
    assert finished.awaiting is None
    # And it is not a question to whoever asked: nothing marks the run as
    # having asked, and the operator is told it went, not that it waits.
    assert not finished.asked_the_asker
    fresh = await uow.threads.list_for_tenant(f.TENANT, opened_by=PrincipalId("devansh"), limit=1)
    said = fresh[0].messages[-1].text
    assert said.startswith("Sent to alex.r@example.com")
