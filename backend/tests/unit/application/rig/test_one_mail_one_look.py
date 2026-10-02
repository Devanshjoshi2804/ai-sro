"""One mail is read by one look, and that look does the same thing whichever
door made it: the panel's poll (`POST /v1/chat/from-the-mail`) or the worker's
sweep (`LookInTheMailLately`).

QA 2026-09-30 (VETSHOP): the worker's look asked in a chat of its own with a
draft to the sender; the panel's look of another mail showed a bare offer. Both
doors are one `FromTheMail`; what differed was the card the panel drew beside
the question. Here: the backend half -- one question, one draft, and nothing
left for the second door to offer.
"""

from __future__ import annotations

import json
import logging

import pytest

from sro.application.chat.about_an_offer import AskAboutTheOffer
from sro.application.chat.ask_the_asker import DRAFTED, DraftForTheAsker
from sro.application.chat.converse import Converse
from sro.application.chat.from_the_mail import FromTheMail, LookedInTheMail
from sro.application.chat.look_lately import LookInTheMailLately
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.execution.workflow_runs import StartWorkflowRun
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.application.observation.record_attempt import RecordAttempt
from sro.application.runtime.answer_run import AnswerRun
from sro.domain.chat.asking import NEEDS, Pending
from sro.domain.chat.thread import Thread
from sro.interface.http.schemas import FromTheMailResponse
from tests import factories as f
from tests.unit.application.rig.test_a_job_declares_its_fields import _field
from tests.unit.application.rig.test_from_the_mail import (
    CTX,
    JOB,
    _found,
    _Gathers,
    _mail,
    _Mailbox,
    _Reads,
    mail_world,
)
from tests.unit.fakes import (
    FakeClock,
    FakeDurableExecution,
    FakeEmbedder,
    FakeIdFactory,
    FakeUnitOfWork,
)

THREAD = "t-1"


def _asker(body: str) -> str:
    return json.dumps(
        {
            "id": THREAD,
            "messages": [
                {
                    "id": "m-1",
                    "from": "Tanisha <tanisha@example.com>",
                    "subject": "vet shops",
                    "body": body,
                    "rfc822_message_id": "<a@mail>",
                }
            ],
        }
    )


def _reads(**values: str) -> _Reads:
    return _Reads(
        {
            "job": JOB,
            "values": [
                {"field": name, "value": value, "quote": value} for name, value in values.items()
            ],
            "missing": [name for name in ("Customer Type",) if name not in values],
            "sure": True,
        }
    )


class _Doors:
    """Both doors, wired the way `container.py` wires them: a fresh
    `FromTheMail` each, over one store and one mailbox, the ask drafting to
    whoever sent the mail."""

    def __init__(self, uow: FakeUnitOfWork, start: StartWorkflowRun, **values: str) -> None:
        self.uow = uow
        self.start = start
        self.values = values
        self.gather: _Gathers | None = None
        self.reading: dict[str, object] | None = None
        body = " ".join(["please add a customer type", *values.values()])
        self.mailbox = _Mailbox(
            search=_found("m-1"),
            **{
                "m-1": _mail(body, THREAD),
                THREAD: _asker(body),
            },
        )

    def look(self) -> FromTheMail:
        clock, ids = FakeClock(), FakeIdFactory()
        drafter = DraftForTheAsker(self.uow, self.mailbox, clock, ids, servers={})

        async def drafts(ctx: RequestContext, pending: Pending, thread: str, asked: str) -> bool:
            return await drafter.execute(ctx, pending, question=asked, thread=thread)

        return FromTheMail(
            self.uow,
            self.mailbox,
            _Reads(self.reading) if self.reading is not None else _reads(**self.values),
            answer=AnswerRun(self.uow, FakeDurableExecution()),
            gather=self.gather,
            clock=clock,
            ids=ids,
            start=self.start,
            attempts=RecordAttempt(self.uow, FakeIdFactory(), FakeClock()),
            asks=AskAboutTheOffer(self.uow, clock, ids, drafts),
            servers={},
        )

    def reply(self, said: str, value: str) -> None:
        """The sender answers on the same thread, as a mail of its own."""
        first = " ".join(["please add a customer type", *self.values.values()])
        self.mailbox = _Mailbox(
            search=_found("m-2", "m-1"),
            **{
                "m-1": _mail(first, THREAD),
                "m-2": json.dumps(
                    {"id": "m-2", "subject": "Re: vet shops", "body": said, "thread_id": THREAD}
                ),
                THREAD: _asker(first),
            },
        )
        self.reading = {
            "job": JOB,
            "values": [{"field": "Customer Type", "value": value, "quote": value}],
            "missing": [],
            "sure": True,
        }

    async def panel(self) -> FromTheMailResponse:
        return FromTheMailResponse.of(await self.look().execute(CTX))

    async def worker(self) -> dict[str, LookedInTheMail]:
        return await LookInTheMailLately(self.uow, self.look(), (f.TENANT.value,)).execute()

    async def chat(self) -> Thread:
        found = await ReadThreads(self.uow).asking(CTX, THREAD)
        assert found is not None, "the mail was never asked about"
        return found


async def _doors(**values: str) -> _Doors:
    world = await mail_world(sure=True, values={}, steel=True, thread=THREAD)
    return _Doors(world.uow, world.start, **values)


def _kinds(chat: Thread) -> list[str]:
    return [str((one.decision or {}).get("kind")) for one in chat.messages]


async def test_the_panel_s_look_asks_as_the_worker_s_does_and_offers_no_card() -> None:
    panel, worker = await _doors(), await _doors()

    said = await panel.panel()
    await worker.worker()

    assert _kinds(await panel.chat()) == _kinds(await worker.chat()) == [NEEDS, DRAFTED]
    assert [one.text for one in (await panel.chat()).messages] == [
        one.text for one in (await worker.chat()).messages
    ]
    (offer,) = said.offered
    assert offer.asked, "the panel would draw an offer beside the question"


async def test_the_panel_then_the_worker_is_one_question_and_one_draft() -> None:
    doors = await _doors()

    await doors.panel()
    swept = await doors.worker()

    assert _kinds(await doors.chat()) == [NEEDS, DRAFTED]
    assert all(one.read == 0 for one in swept.values()), "the mail was read twice"


async def test_the_worker_then_the_panel_is_one_question_and_nothing_to_offer() -> None:
    doors = await _doors()

    await doors.worker()
    said = await doors.panel()

    assert _kinds(await doors.chat()) == [NEEDS, DRAFTED]
    assert said.offered == [], "the second door offered a mail already asked about"


async def test_a_value_the_box_will_not_hold_is_logged_as_refused_not_as_found(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """V4: the log said "gathered 1 of 1 (every value was found in the
    mailbox)" for a VETSHOP whose code the box would not take."""
    doors = await _doors(**{"Customer Type": "PHARM26"})
    await doors.uow.knowledge.add(_field("customerType", ["Customer Type"], 4))
    doors.gather = _Gathers(**{"Customer Type": "PHARM26"})

    with caplog.at_level(logging.INFO):
        said = await doors.panel()

    assert "Customer Type is 7 characters, takes 4" in caplog.text
    (offer,) = said.offered
    assert offer.asked and not offer.started
    assert "What should it be?" in (await doors.chat()).messages[0].text


async def test_a_reply_that_completes_the_values_starts_the_run_at_once() -> None:
    """YPHD on QA (2026-09-30): the reply "customer type :- YPHD" answered the
    question, and the chat then offered the job and waited two minutes for a
    "yes". A sure mail whose values are all there starts at once (Q1); so does
    one completed by its sender's reply."""
    doors = await _doors()
    await doors.panel()
    doors.reply("customer type :- YPHD", "YPHD")

    await doors.panel()

    (run,) = await doors.uow.workflow_runs.for_workflow(f.TENANT, JOB)
    assert run.values.get("Customer Type") == "YPHD"
    assert run.offer == "mail:m-1", "the reply's run is not the question's one offer"
    assert "job" not in _kinds(await doors.chat()), "the reply was offered, not started"
    said = " ".join(one.text for one in (await doors.chat()).messages)
    assert "Customer Type = 'YPHD' (the reply)" in said, "the chat does not say what it ran with"


async def test_a_reply_after_the_operator_answered_in_the_chat_starts_no_second_run() -> None:
    doors = await _doors()
    await doors.panel()
    chat = await doors.chat()
    converse = Converse(
        doors.uow,
        ResolveIntent(doors.uow, PlanTask(Retrieve(doors.uow, FakeEmbedder()))),
        FakeClock(),
        FakeIdFactory(),
        start=doors.start,
    )
    await converse.execute(CTX, thread_id=chat.id, text="YPHD")
    doors.reply("customer type :- YPHD", "YPHD")

    await doors.panel()

    assert len(await doors.uow.workflow_runs.for_workflow(f.TENANT, JOB)) == 1
