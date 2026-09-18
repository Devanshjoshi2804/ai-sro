"""Asking whoever sent the request, and the rules that keep it safe.

A mail cannot be unsent, it leaves the company over the operator's name, and
it goes to somebody outside every system here. So the properties under test
are not "does it write a nice mail" -- that is next door in
`tests/unit/domain/chat/test_asking_the_asker.py` -- but the four that make it
safe to have built at all:

    nothing sends without a press, the words sent are the words read, one mail
    per run whatever happens to the process, and a run nobody can ask about is
    left alone rather than guessed at.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sro.application.chat.ask_the_asker import DRAFTED, DraftForTheAsker, SendTheDraft
from sro.application.context import RequestContext
from sro.application.ports.tools import ToolResult, ToolsUnavailable
from sro.domain.chat.asking import Pending
from sro.domain.execution.waiting import as_said, waiting_on
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.shared.identifiers import PrincipalId, TenantId
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("devansh"))
JOB = "wfl_1"
THREAD = "t-9"


class _Mailbox:
    """A connector that answers, and remembers every send it was asked for."""

    def __init__(self, *, sender: str = "Tanisha Pradhan <tanisha@example.com>") -> None:
        self.sent: list[dict[str, str]] = []
        self._sender = sender
        self.unavailable = False

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
        if self.unavailable:
            raise ToolsUnavailable("the mailbox is not reachable")
        if tool == "send_message":
            self.sent.append(dict(arguments))
            return ToolResult(text=json.dumps({"status": "sent", "id": "m-sent"}))
        return ToolResult(
            text=json.dumps(
                {
                    "id": THREAD,
                    "messages": [
                        {
                            "id": "m-1",
                            "from": self._sender,
                            "subject": "Customer type for the SRO pilot",
                            "rfc822_message_id": "<abc@mail>",
                            "body": "please set one up",
                        },
                        {"id": "m-2", "from": "devansh <devansh@greyorange.com>", "body": "ok"},
                    ],
                }
            )
        )


def _pending(**over: object) -> Pending:
    fields: dict[str, object] = {
        "workflow_id": JOB,
        "title": "Create a Customer Type",
        "values": {"Customer Type": "NEWSROTEST"},
        "missing": ("Customer Type",),
        "limits": {"Customer Type": 4},
    }
    fields.update(over)
    return Pending(**fields)  # type: ignore[arg-type]


async def _a_run(uow: FakeUnitOfWork, *, thread: str = THREAD, asked: bool = False) -> WorkflowRun:
    run = WorkflowRun(
        id="run_1",
        tenant=f.TENANT.value,
        workflow_id=JOB,
        device_id="dev-1",
        values={"Customer Type": "NEWSROTEST"},
        started_by="devansh",
        live=True,
        allow_focus=True,
        started_at=datetime.now(tz=UTC).isoformat(),
        outcome="stopped",
        needs=["Customer Type"],
        asked_the_asker=asked,
        awaiting=as_said(waiting_on("gmail", thread, now=datetime.now(tz=UTC))),
    )
    await uow.workflow_runs.save(run)
    return run


def _drafter(uow: FakeUnitOfWork, mailbox: _Mailbox) -> DraftForTheAsker:
    return DraftForTheAsker(uow, mailbox, FakeClock(), FakeIdFactory())


async def test_a_draft_is_put_in_front_of_somebody_and_nothing_is_sent() -> None:
    """The whole design in one assertion. What drafts never sends."""
    uow, mailbox = FakeUnitOfWork(), _Mailbox()
    await _a_run(uow)

    assert await _drafter(uow, mailbox).execute(CTX, "run_1", _pending()) is True

    assert mailbox.sent == [], "a draft reached the mailbox without anybody pressing anything"
    threads = await uow.threads.list_for_tenant(f.TENANT, opened_by=PrincipalId("devansh"), limit=1)
    decision = threads[0].messages[-1].decision
    assert decision is not None and decision["kind"] == DRAFTED
    # Addressed to whoever ASKED, not to the operator who is reading it.
    assert decision["to"] == "tanisha@example.com"
    assert decision["thread"] == THREAD
    assert decision["in_reply_to"] == "<abc@mail>"
    assert "needs to be 4 characters or fewer" in str(decision["body"])


async def test_the_words_sent_are_the_words_that_were_read() -> None:
    """The panel sends an id; the door re-reads the draft. A door that sent a
    body handed to it would be one where what goes out and what was read are
    two different things."""
    uow, mailbox = FakeUnitOfWork(), _Mailbox()
    await _a_run(uow)
    await _drafter(uow, mailbox).execute(CTX, "run_1", _pending())
    threads = await uow.threads.list_for_tenant(f.TENANT, opened_by=PrincipalId("devansh"), limit=1)
    drafted = threads[0].messages[-1]

    to = await SendTheDraft(uow, mailbox, FakeClock(), FakeIdFactory()).execute(
        CTX, threads[0].id, drafted.id
    )

    assert to == "tanisha@example.com"
    (sent,) = mailbox.sent
    assert sent["to"] == "tanisha@example.com"
    assert sent["body"] == drafted.decision["body"]  # type: ignore[index]
    assert sent["subject"] == drafted.decision["subject"]  # type: ignore[index]
    # Inside the conversation it answers, or the reply lands where nothing is
    # waiting for it.
    assert sent["thread_id"] == THREAD
    assert sent["in_reply_to"] == "<abc@mail>"


async def test_one_mail_per_run_however_many_presses() -> None:
    """A second press lands in the gap between a check and a mailbox. The claim
    is taken before the send for exactly that."""
    uow, mailbox = FakeUnitOfWork(), _Mailbox()
    await _a_run(uow)
    await _drafter(uow, mailbox).execute(CTX, "run_1", _pending())
    threads = await uow.threads.list_for_tenant(f.TENANT, opened_by=PrincipalId("devansh"), limit=1)
    drafted = threads[0].messages[-1]
    sender = SendTheDraft(uow, mailbox, FakeClock(), FakeIdFactory())

    assert await sender.execute(CTX, threads[0].id, drafted.id) == "tanisha@example.com"
    assert await sender.execute(CTX, threads[0].id, drafted.id) == ""

    assert len(mailbox.sent) == 1, "one request, two mails"


async def test_a_run_that_has_already_asked_is_not_drafted_for_again() -> None:
    """Read off the row rather than counted in a process: a worker that
    restarted between two stops must not buy anybody a second mail."""
    uow, mailbox = FakeUnitOfWork(), _Mailbox()
    await _a_run(uow, asked=True)

    assert await _drafter(uow, mailbox).execute(CTX, "run_1", _pending()) is False


async def test_a_run_from_no_mailbox_asks_nobody() -> None:
    """Not every run has somebody to ask. A press on a page has no
    conversation behind it, and inventing a recipient is the guess the whole
    ladder refuses."""
    uow, mailbox = FakeUnitOfWork(), _Mailbox()
    run = await _a_run(uow)
    run.awaiting = None
    await uow.workflow_runs.save(run)

    assert await _drafter(uow, mailbox).execute(CTX, "run_1", _pending()) is False
    assert mailbox.sent == []


async def test_a_conversation_naming_no_sender_is_left_alone() -> None:
    """An empty answer means nobody to ask, which is a thing this says rather
    than guesses past."""
    uow = FakeUnitOfWork()
    mailbox = _Mailbox(sender="somebody with no address at all")
    await _a_run(uow)

    assert await _drafter(uow, mailbox).execute(CTX, "run_1", _pending()) is False


async def test_a_run_short_of_nothing_writes_to_nobody() -> None:
    uow, mailbox = FakeUnitOfWork(), _Mailbox()
    await _a_run(uow)

    assert await _drafter(uow, mailbox).execute(CTX, "run_1", _pending(missing=())) is False


async def test_a_mailbox_that_could_not_be_reached_keeps_the_claim() -> None:
    """A send that may have gone out and cannot be shown to have is not one to
    try again. The same rule the write ladder keeps, and for a stronger reason:
    a duplicate mail cannot be deleted afterwards."""
    uow, mailbox = FakeUnitOfWork(), _Mailbox()
    await _a_run(uow)
    await _drafter(uow, mailbox).execute(CTX, "run_1", _pending())
    threads = await uow.threads.list_for_tenant(f.TENANT, opened_by=PrincipalId("devansh"), limit=1)
    drafted = threads[0].messages[-1]
    mailbox.unavailable = True

    assert (
        await SendTheDraft(uow, mailbox, FakeClock(), FakeIdFactory()).execute(
            CTX, threads[0].id, drafted.id
        )
        == ""
    )

    run = await uow.workflow_runs.get(f.TENANT, "run_1")
    assert run is not None and run.asked_the_asker is True, "a retry could send it twice"


async def test_a_press_on_one_draft_does_not_send_another() -> None:
    """Two runs can both be waiting. By id and never "the newest draft"."""
    uow, mailbox = FakeUnitOfWork(), _Mailbox()
    await _a_run(uow)
    await _drafter(uow, mailbox).execute(CTX, "run_1", _pending())
    threads = await uow.threads.list_for_tenant(f.TENANT, opened_by=PrincipalId("devansh"), limit=1)
    drafted = threads[0].messages[-1]

    nothing = await SendTheDraft(uow, mailbox, FakeClock(), FakeIdFactory()).execute(
        CTX, threads[0].id, "msg_that_is_not_the_draft"
    )

    assert nothing == ""
    assert mailbox.sent == []
    assert drafted.decision is not None
