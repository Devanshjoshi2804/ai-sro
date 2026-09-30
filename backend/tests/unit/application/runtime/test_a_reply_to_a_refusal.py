"""A mail reply to a refused-value question is read for a NEW value: the
refused one is never re-run because a reply (any reply) came in."""

from __future__ import annotations

import json

from sro.application.chat.from_the_mail import FromTheMail
from sro.application.runtime.answer_run import AnswerRun
from tests.unit.application.rig.test_from_the_mail import _found, _Mailbox, _Reads
from tests.unit.application.runtime.test_a_refused_write import (
    CTX,
    THREAD,
    _Asking,
    _chat,
    _refused_run,
)
from tests.unit.fakes import FakeClock, FakeDurableExecution, FakeIdFactory
from tests.unit.runtime_support import WORKFLOW, SteelRun

ENVELOPE = {"thread": THREAD, "subject": "new customer type", "sender": "tanisha@example.com"}


def _reply(said: str) -> str:
    return json.dumps(
        {"id": "m-2", "subject": "Re: x", "body": said, "thread_id": THREAD, "from": "x"}
    )


async def _replied(
    world: SteelRun, asking: _Asking, said: str, *reading: dict[str, object]
) -> None:
    await FromTheMail(
        world.uow,
        _Mailbox(search=_found("m-2"), **{"m-2": _reply(said)}),
        _Reads(*reading),
        answer=AnswerRun(world.uow, FakeDurableExecution()),
        clock=FakeClock(),
        ids=FakeIdFactory(),
        start=asking.start,
    ).execute(CTX)


def _new_runs(world: SteelRun) -> list[dict[str, str]]:
    return [
        dict(one.values) for one in world.uow.workflow_runs.rows.values() if one.id != world.run_id
    ]


async def test_a_reply_with_a_new_value_starts_one_run_with_the_new_value() -> None:
    world, asking = await _refused_run(mail=ENVELOPE)
    await _chat(world, THREAD)

    await _replied(
        world,
        asking,
        "Description :- Vets",
        {
            "job": WORKFLOW.id,
            "values": [{"field": "Description", "value": "Vets", "quote": "Vets"}],
            "missing": [],
            "sure": True,
        },
    )

    assert _new_runs(world) == [{"Customer Type": "GT2", "Description": "Vets"}]


async def test_a_reply_that_gives_no_new_value_never_reruns_the_refused_write() -> None:
    world, asking = await _refused_run(mail=ENVELOPE)
    await _chat(world, THREAD)

    await _replied(world, asking, "thanks")

    assert _new_runs(world) == []


_VETS: dict[str, object] = {
    "job": WORKFLOW.id,
    "values": [{"field": "Description", "value": "Vets", "quote": "Vets"}],
    "missing": [],
    "sure": True,
}


async def test_the_mail_then_the_chat_answering_the_same_refusal_start_one_run() -> None:
    world, asking = await _refused_run(mail=ENVELOPE)
    chat = await _chat(world, THREAD)

    await _replied(world, asking, "Description :- Vets", _VETS)
    await asking.converse(world).execute(CTX, thread_id=chat.id, text="Vets")

    assert len(_new_runs(world)) == 1


async def test_the_chat_then_the_mail_answering_the_same_refusal_start_one_run() -> None:
    world, asking = await _refused_run(mail=ENVELOPE)
    chat = await _chat(world, THREAD)

    await asking.converse(world).execute(CTX, thread_id=chat.id, text="Vets")
    await _replied(world, asking, "Description :- Vets", _VETS)

    assert len(_new_runs(world)) == 1
