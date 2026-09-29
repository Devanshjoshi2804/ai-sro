"""The mail door, seen and said (QA 2026-09-29).

A mail asked for a job, the look started it on Steel, and it held in 12 s --
while the panel showed nothing that said a MAIL arrived. And "check mail for
any new work", typed in the chat, was walked on the screen as a task nobody had
demonstrated.

Held here, through the real reader, the real look and the real start:
- a chat request to check the mail runs the look now and says, per message,
  what it did;
- a run the look starts carries the mail it came from -- subject, sender, the
  thread, when it arrived -- and never its body;
- the operator's thread says that mail arrived and which job it started, with
  the run named, so the chat draws the run under it;
- two looks at once read each mail once, and the chat says a mail is being read
  elsewhere rather than that nothing arrived.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from sro.application.chat.converse import Converse, StartThread
from sro.application.chat.mailbox import SERVER, mail_key
from sro.application.chat.read_chat import ReadChat
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.execution.workflow_runs import ListWorkflowRuns
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.domain.chat.thread import Speaker, Thread
from sro.domain.execution.mail_job import LOOK_IN_THE_MAIL
from sro.domain.execution.workflow_run import OfferTaken
from sro.domain.shared.identifiers import PrincipalId
from sro.interface.http.schemas import WorkflowRunModel
from tests import factories as f
from tests.unit.application.rig.test_from_the_mail import (
    CTX,
    EVERY_VALUE,
    JOB,
    OPERATOR,
    _addressed,
    _found,
    _Mailbox,
    _MailWorld,
    _Reads,
    _request,
    _should_we,
    _sure,
    mail_world,
)
from tests.unit.application.rig.test_start_workflow_run import _starter
from tests.unit.fakes import (
    FakeClock,
    FakeDurableExecution,
    FakeEmbedder,
    FakeIdFactory,
    FakeUnitOfWork,
)
from tests.unit.runtime_support import save_job

BODY = "please add customer type GT2 -- the pallet code is 7781"
SENDER = "Alex R <alex.r@example.com>"
ARRIVED = "Mon, 29 Sep 2026 11:02:07 +0530"


def _a_mail(message: str, subject: str, body: str, thread: str) -> str:
    return json.dumps(
        {
            "id": message,
            "thread_id": thread,
            "from": SENDER,
            "to": "devansh@wh.example",
            "date": ARRIVED,
            "subject": subject,
            "body": body,
        }
    )


def _two_mails() -> _Mailbox:
    return _Mailbox(
        search=_found("m-1", "m-2"),
        **{
            "m-1": _a_mail("m-1", "new type", BODY, "t-1"),
            "m-2": _a_mail("m-2", "Lunch on Friday?", "shall we get lunch", "t-2"),
        },
    )


def _asks_for_the_job() -> dict[str, object]:
    return {
        "job": JOB,
        "values": [{"field": "Customer Type", "value": "GT2", "quote": "GT2"}],
        "missing": [],
        "sure": True,
    }


def _nothing() -> dict[str, object]:
    return {"job": None, "values": [], "missing": [], "sure": True}


def _check_mail() -> _Reads:
    """The chat reader, placing the sentence on the look."""
    return _Reads({"job": LOOK_IN_THE_MAIL, "values": [], "missing": [], "sure": True})


def _chat(world: _MailWorld, mailbox: _Mailbox, reads: _Reads, chat: _Reads) -> Converse:
    clock, ids = FakeClock(datetime.now(tz=UTC)), FakeIdFactory()
    return Converse(
        world.uow,
        ResolveIntent(world.uow, PlanTask(Retrieve(world.uow, FakeEmbedder()))),
        clock,
        ids,
        reads_jobs=ReadChat(world.uow, asker=chat, clock=clock, cap_usd=100.0),
        start=world.start,
        look=world.look(mailbox, reads),
    )


async def _said(converse: Converse, world: _MailWorld, text: str) -> Thread:
    thread = await ReadThreads(world.uow).current(CTX) or await StartThread(
        world.uow, FakeClock(), FakeIdFactory()
    ).execute(CTX)
    return await converse.execute(CTX, thread_id=thread.id, text=text)


async def test_check_mail_in_the_chat_looks_now_and_says_what_each_mail_came_to() -> None:
    world = await mail_world(sure=True, values=EVERY_VALUE, steel=True)
    chat = _check_mail()
    converse = _chat(world, _two_mails(), _Reads(_asks_for_the_job(), _nothing()), chat)

    said = await _said(converse, world, "check mail for any new work")

    offered = [one["id"] for one in _request(chat.saw[0])["jobs"]]
    assert LOOK_IN_THE_MAIL in offered, "the reader was never offered the look"
    reply = said.messages[-1]
    assert reply.speaker is Speaker.ASSISTANT
    assert (reply.decision or {}).get("kind") == "mail_looked"
    assert "'new type' — started Save the customer type" in reply.text, reply.text
    assert "a mail that asks for no job here: 'Lunch on Friday?'" in reply.text, reply.text
    assert "Nobody has demonstrated" not in reply.text
    assert len(world.durable.runs_started) == 1
    words = [one.text for one in said.messages]
    assert words.index("check mail for any new work") < len(words) - 1, (
        "the operator's words come before what the look found"
    )


async def test_a_second_check_finds_nothing_new_and_starts_nothing() -> None:
    world = await mail_world(sure=True, values=EVERY_VALUE, steel=True)
    mailbox = _two_mails()
    first = _chat(world, mailbox, _Reads(_asks_for_the_job(), _nothing()), _check_mail())
    await _said(first, world, "check mail for any new work")
    again = _chat(world, mailbox, _Reads(_asks_for_the_job(), _nothing()), _check_mail())

    said = await _said(again, world, "check gmail for any new work")

    assert "no mail has arrived since the last look" in said.messages[-1].text
    assert len(world.durable.runs_started) == 1, "a mail read twice started twice"


async def test_a_mail_another_look_is_reading_is_said_and_left_to_it() -> None:
    """The worker's poll and the chat look at once: one reading of each mail."""
    world = await mail_world(sure=True, values=EVERY_VALUE, steel=True)
    await world.uow.tool_calls.remember(
        f.TENANT, "reading:m-1", tool="read a mail for what it asks", at=datetime.now(tz=UTC)
    )
    reads = _Reads(_nothing())
    converse = _chat(world, _two_mails(), reads, _check_mail())

    said = await _said(converse, world, "check mail for any new work")

    assert "1 mail is being read by another look right now" in said.messages[-1].text
    assert world.durable.runs_started == []
    assert len(reads.saw) == 1, "the mail the other look holds was read here too"


async def test_the_other_chat_door_never_places_the_look() -> None:
    """`/v1/ask` reads the same words and can only offer a job; a look is the
    conversation's to do, so it is never offered there as one."""
    world = await mail_world(sure=True, values=EVERY_VALUE, steel=True)
    reads = _Reads(_nothing())

    await ReadChat(world.uow, asker=reads, clock=FakeClock(), cap_usd=100.0).execute(
        CTX, utterance="check mail for any new work"
    )

    assert LOOK_IN_THE_MAIL not in [one["id"] for one in _request(reads.saw[0])["jobs"]]


async def test_a_run_a_mail_started_carries_the_mail_and_never_its_body() -> None:
    world = await mail_world(sure=True, values=EVERY_VALUE, steel=True)
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _a_mail("m-1", "new type", BODY, "t-1")})

    await world.look(mailbox, _Reads(_asks_for_the_job())).execute(CTX)

    (run,) = await world.uow.workflow_runs.for_workflow(f.TENANT, JOB)
    assert run.mail == {
        "subject": "new type",
        "sender": SENDER,
        "thread": "t-1",
        "arrived": "2026-09-29T11:02:07+05:30",
    }
    assert "7781" not in json.dumps(run.mail), "the body travelled with the run"
    wire = WorkflowRunModel.of(run)
    assert wire.mail is not None and wire.mail.link == "https://mail.google.com/mail/#all/t-1"
    assert wire.offer == "mail:m-1", "the panel cannot tell this mail's card from its run"


async def test_the_thread_says_the_mail_arrived_and_names_the_run_it_started() -> None:
    world = await mail_world(sure=True, values=EVERY_VALUE, steel=True)
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _a_mail("m-1", "new type", BODY, "t-1")})

    await world.look(mailbox, _Reads(_asks_for_the_job())).execute(CTX)

    (run,) = await world.uow.workflow_runs.for_workflow(f.TENANT, JOB)
    thread = await ReadThreads(world.uow).current(CTX)
    assert thread is not None
    (told,) = [one for one in thread.messages if (one.decision or {}).get("run_id") == run.id]
    assert told.decision == {
        "kind": "run",
        "run_id": run.id,
        "offer": "mail:m-1",
        "mail_thread": "t-1",
    }
    assert "A mail arrived from Alex R <alex.r@example.com>: 'new type'" in told.text
    assert "Save the customer type" in told.text and "Customer Type GT2" in told.text
    assert "7781" not in told.text


async def test_a_run_started_on_a_mail_conversation_knows_the_mail_it_is_about() -> None:
    """A yes in the panel to a mail's question starts the run on that mail's
    conversation: it is a mail run too, and says which thread."""
    uow = FakeUnitOfWork()
    await save_job(uow, JOB)
    start = _starter(
        uow,
        durable=FakeDurableExecution(),
        steel_tenants=frozenset({f.TENANT.value}),
        clock=FakeClock(datetime.now(tz=UTC) - timedelta(seconds=1)),
    )

    run = await start.execute(
        CTX,
        workflow_id=JOB,
        device_id=None,
        values={"Customer Type": "GT2"},
        live=True,
        allow_focus=False,
        conversation=(SERVER, "t-9"),
    )
    plain = await start.execute(
        CTX,
        workflow_id=JOB,
        device_id=None,
        values={"Customer Type": "GT3"},
        live=True,
        allow_focus=False,
    )

    assert run.mail == {"thread": "t-9"}
    assert plain.mail is None


# One mail, one offer, one run (the user, 2026-09-29): the mail reader started
# the run itself, and a later surface offered that same mail again.


async def test_a_card_press_on_a_mail_the_reader_already_ran_lands_on_that_run() -> None:
    world = await mail_world(sure=True, values=EVERY_VALUE, steel=True)
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _a_mail("m-1", "new type", BODY, "t-1")})
    await world.look(mailbox, _Reads(_asks_for_the_job())).execute(CTX)
    (ran,) = await world.uow.workflow_runs.for_workflow(f.TENANT, JOB)

    with pytest.raises(OfferTaken) as taken:
        await world.start.execute(
            CTX,
            workflow_id=JOB,
            device_id=None,
            values=EVERY_VALUE,
            live=True,
            allow_focus=True,
            conversation=(SERVER, "t-1"),
            offer=mail_key("m-1"),
        )

    assert taken.value.run_id == ran.id
    assert [one for one, _ in world.durable.runs_started] == [ran.id]


async def test_a_chat_yes_on_a_mail_whose_run_already_started_answers_that_run() -> None:
    """Asked about first, started by the press, then a yes in the chat."""
    world = await mail_world(sure=True, values=EVERY_VALUE, steel=True)
    await world.polling(_addressed(OPERATOR, "colleague@example.com"), _sure()).execute()
    asked = await _should_we(world)
    pressed = await world.start.execute(
        CTX,
        workflow_id=JOB,
        device_id=None,
        values=EVERY_VALUE,
        live=True,
        allow_focus=True,
        offer=str(asked["offer"]),
    )
    await world.start.start_on_steel(CTX, pressed)
    converse = _chat(world, _two_mails(), _Reads(), _check_mail())
    thread = await ReadThreads(world.uow).asking(CTX, str(asked["mail_thread"]))
    assert thread is not None

    said = await converse.execute(CTX, thread_id=thread.id, text="yes")

    assert str(asked["offer"]).startswith("mail:")
    told = said.messages[-1]
    assert (told.decision or {}).get("run_id") == pressed.id, told
    assert "already running" in told.text
    assert [one for one, _ in world.durable.runs_started] == [pressed.id]


async def test_pending_work_from_mail_shows_the_run_the_reader_started_never_an_offer() -> None:
    world = await mail_world(sure=True, values=EVERY_VALUE, steel=True)
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _a_mail("m-1", "new type", BODY, "t-1")})
    await world.look(mailbox, _Reads(_asks_for_the_job())).execute(CTX)
    converse = _chat(world, mailbox, _Reads(), _check_mail())

    said = await _said(converse, world, "show me any pending work from mail")

    reply = said.messages[-1].text
    assert "no mail has arrived since the last look" in reply, reply
    assert "'new type' — already running: Save the customer type (Customer Type GT2)" in reply
    assert not [one for one in said.messages if (one.decision or {}).get("kind") == "job"]
    assert len(world.durable.runs_started) == 1


async def test_a_mail_run_that_ended_is_said_as_how_it_ended() -> None:
    world = await mail_world(sure=True, values=EVERY_VALUE, steel=True)
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _a_mail("m-1", "new type", BODY, "t-1")})
    await world.look(mailbox, _Reads(_asks_for_the_job())).execute(CTX)
    (run,) = await world.uow.workflow_runs.for_workflow(f.TENANT, JOB)
    async with world.uow as uow:
        run.outcome, run.finished_at = "held", "2026-09-29T05:42:00+00:00"
        await uow.workflow_runs.save(run)
        await uow.commit()
    converse = _chat(world, mailbox, _Reads(), _check_mail())

    said = await _said(converse, world, "check mail")

    assert "'new type' — done at 05:42 UTC: Save the customer type" in said.messages[-1].text


async def test_the_list_the_panel_polls_can_keep_only_the_caller_s_runs() -> None:
    """Home draws a card per mail run; a colleague's mail is not theirs."""
    world = await mail_world(sure=True, values=EVERY_VALUE, steel=True)
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _a_mail("m-1", "new type", BODY, "t-1")})
    await world.look(mailbox, _Reads(_asks_for_the_job())).execute(CTX)
    colleague = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("colleague"))
    listing = ListWorkflowRuns(world.uow)

    theirs = await listing.execute(colleague, workflow_id=None, limit=20, awaiting=False, mine=True)
    mine = await listing.execute(CTX, workflow_id=None, limit=20, awaiting=False, mine=True)
    everyone = await listing.execute(colleague, workflow_id=None, limit=20, awaiting=False)

    assert theirs == ()
    assert [run.mail is not None for run in mine] == [True]
    assert len(everyone) == 1


async def test_a_thread_that_cannot_be_told_leaves_the_started_mail_claimed() -> None:
    """A crash between the start and the telling: the run stands, the mail
    stays read, and the next look reads nothing twice."""
    world = await mail_world(sure=True, values=EVERY_VALUE, steel=True)
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _a_mail("m-1", "new type", BODY, "t-1")})
    saving = world.uow.threads.save

    async def refuses(thread: Thread) -> None:
        if any((one.decision or {}).get("kind") == "run" for one in thread.messages):
            raise RuntimeError("the thread store went away")
        await saving(thread)

    world.uow.threads.save = refuses  # type: ignore[method-assign]
    reads = _Reads(_asks_for_the_job(), _asks_for_the_job())
    looked = await world.look(mailbox, reads).execute(CTX)
    world.uow.threads.save = saving  # type: ignore[method-assign]
    await world.look(mailbox, reads).execute(CTX)

    assert [one.started for one in looked.offered] == [True]
    assert len(reads.saw) == 1, "the started mail was read again"
    assert len(world.durable.runs_started) == 1
