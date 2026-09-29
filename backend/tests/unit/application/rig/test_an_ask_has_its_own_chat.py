"""A question, the mail drafted about it, the answer and the run it starts are
one chat of their own.

Seen on QA 2026-09-29 (tenant greyorange): a mail asked for customer type
VETCLINIC, a box that holds 4. The question and the draft to the sender were
written into the operator's one long thread, under every earlier job; the
draft still offered Send it after the operator had typed VETC, and the earlier
PHARM26 draft was sent after its question had been answered -- asking the
sender for a value already given, then saying "I will carry on when they
reply" about a run that was done. The run the answer started also lost its
mail's subject, sender and time.

Every test here goes through the doors production uses: the mail door's ask
(`AskAboutTheOffer`), the drafter it is wired to, `Converse` taking the answer
and starting the run, and `SendTheDraft`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping

from sro.application.chat.about_an_offer import AskAboutTheOffer
from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.ask_the_asker import DRAFTED, SENT, DraftForTheAsker, SendTheDraft
from sro.application.chat.converse import StartThread
from sro.application.chat.read_threads import ReadThreads
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import IdFactory
from sro.application.ports.tools import ToolResult
from sro.domain.chat.asking import NEEDS, Pending
from sro.domain.chat.thread import Message, Speaker, Thread
from sro.domain.shared.identifiers import PrincipalId, TenantId
from tests import factories as f
from tests.unit.application.rig.test_asking_the_asker import THREAD
from tests.unit.application.rig.test_asking_the_asker import _Mailbox as _Asker
from tests.unit.application.test_a_yes_starts_the_run import CTX, JOB, _World
from tests.unit.fakes import FakeClock, FakeIdFactory

ENVELOPE = {
    "subject": "new customer type - vet clinics",
    "sender": "Devansh Joshi <devanshpersonal2804@gmail.com>",
    "arrived": "2026-09-29T03:22:10-07:00",
}


class _AnsweredMeanwhile(_Asker):
    """A mailbox slow enough that the operator's answer lands while it sends."""

    answer: Callable[[], Awaitable[object]] | None = None

    async def call(
        self,
        tenant_id: TenantId,
        principal_id: PrincipalId,
        server: str,
        tool: str,
        arguments: Mapping[str, str],
    ) -> ToolResult:
        if tool == "send_message" and self.answer is not None:
            await self.answer()
        return await super().call(tenant_id, principal_id, server, tool, arguments)


class _Ask:
    """The mail door's ask, wired the way `container.py` wires it."""

    def __init__(self, world: _World, mailbox: _Asker | None = None) -> None:
        self.world = world
        self.mailbox = mailbox or _Asker()
        self.clock, self.ids = FakeClock(), world.wiring["ids"]
        drafter = DraftForTheAsker(world.uow, self.mailbox, self.clock, self.ids)

        async def drafts(ctx: object, pending: Pending, thread: str, question: str) -> bool:
            return await drafter.execute(CTX, pending, question=question, thread=thread)

        self.door = AskAboutTheOffer(world.uow, self.clock, self.ids, drafts)

    async def asks(self) -> str:
        return await self.door.execute(
            CTX,
            Pending(
                workflow_id=JOB,
                title=self.world.title,
                values={"Customer Type": "VETCLINIC"},
                missing=(),
                limits={"Customer Type": 4},
                mail_thread=THREAD,
            ),
            about=ENVELOPE["subject"],
            mail_thread=THREAD,
            offer="mail:m-1",
            mail=ENVELOPE,
        )

    async def chat(self) -> Thread:
        found = await ReadThreads(self.world.uow).asking(CTX, THREAD)
        assert found is not None, "the question has no chat of its own"
        return found

    def sender(self) -> SendTheDraft:
        return SendTheDraft(self.world.uow, self.mailbox, self.clock, self.ids)


def _kinds(thread: Thread) -> list[str]:
    return [str((one.decision or {}).get("kind") or one.speaker.value) for one in thread.messages]


def _draft(thread: Thread) -> Message:
    return next(one for one in thread.messages if (one.decision or {}).get("kind") == DRAFTED)


async def _a_long_thread(world: _World) -> Thread:
    long = await StartThread(world.uow, FakeClock(), FakeIdFactory()).execute(CTX)
    await SayWhatHappened(world.uow, FakeClock(), FakeIdFactory()).execute(
        CTX,
        for_operator=CTX.principal_id,
        text="Done: Create a Customer Type (Customer Type = PH26).",
        decision={"kind": "run_done", "run_id": "run_earlier", "outcome": "held"},
    )
    return long


async def test_the_question_and_its_draft_are_one_chat_of_their_own() -> None:
    world = await _World().ready()
    long = await _a_long_thread(world)
    ask = _Ask(world)

    await ask.asks()

    chat = await ask.chat()
    assert _kinds(chat) == [NEEDS, DRAFTED], "question and draft are not side by side"
    assert chat.id != long.id
    current = await ReadThreads(world.uow).current(CTX)
    assert current is not None and current.id == long.id, "the ask took over the operator's chat"
    assert _kinds(await world.uow.threads.get(f.TENANT, long.id)) == ["run_done"], (
        "the question was buried in the long thread as well"
    )


async def test_asking_again_about_one_request_is_the_same_chat() -> None:
    world = await _World().ready()
    ask = _Ask(world)

    await asyncio.gather(ask.asks(), ask.asks())

    mine = await world.uow.threads.list_for_tenant(f.TENANT, opened_by=CTX.principal_id)
    assert len(mine) == 1, "two chats for one request"
    assert _kinds(await ask.chat()).count(DRAFTED) == 1


async def test_an_answer_in_the_chat_starts_the_run_there_and_the_run_reports_there() -> None:
    world = await _World().ready()
    await _a_long_thread(world)
    ask = _Ask(world)
    await ask.asks()
    chat = await ask.chat()

    said = await world.converse().execute(CTX, thread_id=chat.id, text="VETC")

    (run_id,) = await world.runs()
    assert (said.messages[-1].decision or {}).get("run_id") == run_id
    await SayWhatHappened(world.uow, FakeClock(), FakeIdFactory()).execute(
        CTX,
        for_operator=CTX.principal_id,
        text="Done: Create a Customer Type (Customer Type = VETC).",
        decision={"kind": "run_done", "run_id": run_id, "outcome": "held"},
    )
    assert _kinds(await ask.chat())[-1] == "run_done", "the result landed somewhere else"


async def test_the_run_an_answer_starts_keeps_its_mail() -> None:
    """PH88 on QA: the card read "A mail / Arrived" and nothing else."""
    world = await _World().ready()
    ask = _Ask(world)
    await ask.asks()

    await world.converse().execute(CTX, thread_id=(await ask.chat()).id, text="VETC")

    (run_id,) = await world.runs()
    run = await world.uow.workflow_runs.get(f.TENANT, run_id)
    assert run is not None
    assert run.mail == {"thread": THREAD, **ENVELOPE}


async def test_a_draft_whose_question_was_answered_is_never_sent() -> None:
    """PHARM26 on QA: answered at 10:13:50, the stale draft sent at 10:14:21."""
    world = await _World().ready()
    ask = _Ask(world)
    await ask.asks()
    chat = await ask.chat()
    await world.converse().execute(CTX, thread_id=chat.id, text="VETC")

    sent_to = await ask.sender().execute(CTX, chat.id, _draft(chat).id.value)

    assert sent_to == ""
    assert ask.mailbox.sent == [], "the sender was asked for a value given"
    after = await ask.chat()
    assert not any("carry on when they reply" in one.text for one in after.messages)


async def test_a_question_still_standing_can_still_be_asked_by_mail() -> None:
    world = await _World().ready()
    ask = _Ask(world)
    await ask.asks()
    chat = await ask.chat()

    sent_to = await ask.sender().execute(CTX, chat.id, _draft(chat).id.value)

    assert sent_to == "tanisha@example.com"
    assert len(ask.mailbox.sent) == 1
    assert (await ask.chat()).messages[-1].text.endswith("I will carry on when they reply.")


async def test_an_answer_after_the_mail_went_says_so_rather_than_waiting_on_it() -> None:
    world = await _World().ready()
    ask = _Ask(world)
    await ask.asks()
    chat = await ask.chat()
    await ask.sender().execute(CTX, chat.id, _draft(chat).id.value)

    said = await world.converse().execute(CTX, thread_id=chat.id, text="VETC")

    last = said.messages[-1]
    assert last.text.startswith(f"Running {world.title} now.")
    assert "tanisha@example.com was asked by mail before this answer came" in last.text


async def test_an_answer_landing_while_the_mail_is_in_flight_is_not_waited_on() -> None:
    """The press claimed the draft with the question standing; the operator's
    answer landed before the mailbox did. The line after the send must not
    promise to carry on when the sender replies."""
    world = await _World().ready()
    mailbox = _AnsweredMeanwhile()
    ask = _Ask(world, mailbox)
    await ask.asks()
    chat = await ask.chat()
    converse = world.converse()

    async def answer() -> object:
        return await converse.execute(CTX, thread_id=chat.id, text="VETC")

    mailbox.answer = answer

    assert await ask.sender().execute(CTX, chat.id, _draft(chat).id.value) == "tanisha@example.com"

    last = (await ask.chat()).messages[-1]
    assert (last.decision or {}).get("kind") == SENT
    assert "carry on when they reply" not in last.text
    assert "answered here meanwhile" in last.text


async def test_a_run_that_came_up_short_asks_in_the_chat_of_its_mail() -> None:
    """The other door that asks: a run that stopped short of a value. Its
    question goes to the chat of the mail it came from, and the run the answer
    starts keeps that mail."""
    world = await _World().ready()
    ask = _Ask(world)
    await ask.asks()
    chat = await ask.chat()
    await world.converse().execute(CTX, thread_id=chat.id, text="VETC")
    (run_id,) = await world.runs()
    run = await world.uow.workflow_runs.get(f.TENANT, run_id)
    assert run is not None
    run.needs = ["Customer Type"]
    run.outcome = "stopped"
    await world.uow.workflow_runs.save(run)

    await world.start._ask_for_values(CTX, run, world.title)

    asked = (await ask.chat()).messages[-1]
    assert asked.speaker is Speaker.ASSISTANT
    decision = asked.decision or {}
    assert decision.get("kind") == NEEDS and decision.get("from_run") == run_id
    assert decision.get("mail_thread") == THREAD
    await world.converse().execute(CTX, thread_id=chat.id, text="VET1")
    resumed = [one for one in await world.runs() if one != run_id]
    assert resumed, "the answer started nothing"
    again = await world.uow.workflow_runs.get(f.TENANT, resumed[0])
    assert again is not None and again.mail == {"thread": THREAD, **ENVELOPE}


async def test_a_run_with_no_mail_asks_in_a_chat_of_its_own() -> None:
    world = await _World().ready()
    long = await _a_long_thread(world)
    said = await world.converse().execute(CTX, thread_id=long.id, text="create customer type GT2")
    offer = said.messages[-1]
    await world.converse().execute(CTX, thread_id=long.id, text="yes", answering=offer.id.value)
    (run_id,) = await world.runs()
    run = await world.uow.workflow_runs.get(f.TENANT, run_id)
    assert run is not None
    run.needs = ["Customer Type"]
    await world.uow.workflow_runs.save(run)

    await world.start._ask_for_values(CTX, run, world.title)

    chat = await ReadThreads(world.uow).asking(CTX, run_id)
    assert chat is not None and _kinds(chat) == [NEEDS]
    await world.start._ask_for_values(CTX, run, world.title)
    mine = await world.uow.threads.list_for_tenant(
        f.TENANT, opened_by=PrincipalId(CTX.principal_id.value)
    )
    assert len(mine) == 2, "asking twice for one run opened a second chat"


async def test_an_answered_draft_stays_answered_when_the_run_asks_again() -> None:
    """The draft asks about its own question, not whichever stands in the chat.

    The mail asked, a draft was written, the operator answered VETC (the draft
    is refused), the run came up short and asked again in the same chat. The
    old draft must not come back sendable under the new question.
    """
    world = await _World().ready()
    ask = _Ask(world)
    await ask.asks()
    chat = await ask.chat()
    old = _draft(chat)
    await world.converse().execute(CTX, thread_id=chat.id, text="VETC")
    (run_id,) = await world.runs()
    run = await world.uow.workflow_runs.get(f.TENANT, run_id)
    assert run is not None
    run.needs = ["Customer Type"]
    run.outcome = "stopped"
    await world.uow.workflow_runs.save(run)
    await world.start._ask_for_values(CTX, run, world.title)

    sent_to = await ask.sender().execute(CTX, chat.id, old.id.value)

    assert sent_to == ""
    assert ask.mailbox.sent == [], "an answered draft was sent under a newer question"


async def test_a_run_answered_in_its_ask_chat_asks_again_in_that_chat() -> None:
    """A run with no mail asks in a chat keyed by its id. The answer given
    there starts a new run -- a new id -- and when that one comes up short too,
    its question belongs in the chat it was started from, not a third one."""
    world = await _World().ready()
    long = await _a_long_thread(world)
    said = await world.converse().execute(CTX, thread_id=long.id, text="create customer type GT2")
    await world.converse().execute(
        CTX, thread_id=long.id, text="yes", answering=said.messages[-1].id.value
    )
    (first,) = await world.runs()
    run = await world.uow.workflow_runs.get(f.TENANT, first)
    assert run is not None
    run.needs = ["Customer Type"]
    run.outcome = "stopped"
    await world.uow.workflow_runs.save(run)
    await world.start._ask_for_values(CTX, run, world.title)
    chat = await ReadThreads(world.uow).asking(CTX, first)
    assert chat is not None

    await world.converse().execute(CTX, thread_id=chat.id, text="VETC")
    (again,) = [one for one in await world.runs() if one != first]
    resumed = await world.uow.workflow_runs.get(f.TENANT, again)
    assert resumed is not None
    resumed.needs = ["Customer Type"]
    resumed.outcome = "stopped"
    await world.uow.workflow_runs.save(resumed)
    await world.start._ask_for_values(CTX, resumed, world.title)

    mine = await world.uow.threads.list_for_tenant(
        f.TENANT, opened_by=PrincipalId(CTX.principal_id.value)
    )
    assert len(mine) == 2, "the resumed run asked in a chat of its own"
    chat = await world.uow.threads.get(f.TENANT, chat.id)
    assert _kinds(chat)[-1] == NEEDS


async def home_holds_every_standing_question(uow: UnitOfWork, ids: IdFactory) -> None:
    """Home reads the chats whose question STANDS, newest question first -- not
    the newest chats opened. A chat keeps its first `opened_at`, so a fixed
    window over it drops an old chat that was just asked something new."""
    clock = FakeClock()
    say = SayWhatHappened(uow, clock, ids)
    asked = {"kind": NEEDS, "workflow_id": JOB, "missing": ["Customer Type"]}

    async def ask(about: str) -> None:
        clock.advance(60)
        await say.execute(
            CTX,
            for_operator=CTX.principal_id,
            text="What?",
            decision={**asked, "mail_thread": about},
            speaker=Speaker.ASSISTANT,
            about=about,
        )

    for n in range(12):
        await ask(f"t-{n}")
    clock.advance(60)
    await say.execute(
        CTX,
        for_operator=CTX.principal_id,
        text="Running it now.",
        decision={"kind": "job", "workflow_id": JOB, "mail_thread": "t-5", "run_id": "run_5"},
        speaker=Speaker.ASSISTANT,
        about="t-5",
    )
    await ask("t-0")

    home = await ReadThreads(uow).asked(CTX)

    about = [await ReadThreads(uow).asking(CTX, f"t-{n}") for n in range(12)]
    names = {one.id: n for n, one in enumerate(about) if one is not None}
    assert [names[one.id] for one in home] == [0, 11, 10, 9, 8, 7, 6, 4, 3, 2]


async def test_home_holds_an_old_chat_asked_something_new() -> None:
    world = await _World().ready()
    await home_holds_every_standing_question(world.uow, world.wiring["ids"])
