"""A mail reply to a refused-value question is read for a NEW value: the
refused one is never re-run because a reply (any reply) came in."""

from __future__ import annotations

import json

from sro.application.chat.ask_the_asker import DRAFTED, SendTheDraft
from sro.application.chat.from_the_mail import FromTheMail
from sro.application.runtime.answer_run import AnswerRun
from sro.domain.chat.asking import NEEDS
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


def _reply(said: str, sender: str = "") -> str:
    return json.dumps(
        {"id": "m-2", "subject": "Re: x", "body": said, "thread_id": THREAD, "from": sender}
    )


async def _replied(
    world: SteelRun, asking: _Asking, said: str, *reading: dict[str, object], sender: str = ""
) -> None:
    await FromTheMail(
        world.uow,
        _Mailbox(search=_found("m-2"), **{"m-2": _reply(said, sender)}),
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


async def _sent_to_the_sender() -> tuple[SteelRun, _Asking]:
    world, asking = await _refused_run(mail=ENVELOPE)
    chat = await _chat(world, THREAD)
    (draft,) = [one for one in chat.messages if (one.decision or {}).get("kind") == DRAFTED]
    sent = SendTheDraft(world.uow, asking.mailbox, FakeClock(), FakeIdFactory())
    assert await sent.execute(CTX, chat.id, draft.id.value) == "tanisha@example.com"
    return world, asking


async def test_a_reply_from_somebody_the_question_was_not_mailed_to_answers_nothing() -> None:
    world, asking = await _sent_to_the_sender()

    await _replied(world, asking, "Description :- Vets", _VETS, sender="mallory@example.com")

    # It may still be read as a request of its own, but it is never the answer.
    chat = await _chat(world, THREAD)
    assert not [one for one in chat.messages if one.text.startswith("A reply")]


async def test_a_reply_from_the_address_the_question_was_mailed_to_answers_it() -> None:
    world, asking = await _sent_to_the_sender()

    await _replied(
        world, asking, "Description :- Vets", _VETS, sender="Tanisha <TANISHA@example.com>"
    )

    assert _new_runs(world) == [{"Customer Type": "GT2", "Description": "Vets"}]


async def test_what_a_reply_said_is_shown_as_quoted_data_and_bounded() -> None:
    world, asking = await _refused_run(mail=ENVELOPE)
    long = "Vets " + "x" * 400
    await _replied(
        world,
        asking,
        f"Description :- {long}",
        {**_VETS, "values": [{"field": "Description", "value": long, "quote": long}]},
    )

    chat = await _chat(world, THREAD)
    (note,) = [one for one in chat.messages if one.text.startswith("A reply to 'Re: x'")]
    assert "Description 'Vets " in note.text and len(note.text) < 300


async def _question_and_new_run_offers(by_mail: bool) -> tuple[str, list[str]]:
    world, asking = await _refused_run(mail=ENVELOPE)
    chat = await _chat(world, THREAD)
    (question,) = [one for one in chat.messages if (one.decision or {}).get("kind") == NEEDS]
    if by_mail:
        await _replied(world, asking, "Description :- Vets", _VETS)
    else:
        await asking.converse(world).execute(CTX, thread_id=chat.id, text="Vets")
    offers = [one.offer for one in world.uow.workflow_runs.rows.values() if one.id != world.run_id]
    return question.id.value, offers


async def test_the_mail_and_the_panel_start_a_refusal_s_answer_under_the_questions_own_key() -> None:
    # One question, one key: otherwise uq_workflow_runs_one_per_offer cannot
    # stop the operator's typed answer and a mail reply both starting a run.
    for by_mail in (True, False):
        question, offers = await _question_and_new_run_offers(by_mail)
        assert offers == [question], by_mail


async def test_a_display_name_holding_the_asked_address_does_not_answer_for_its_owner() -> None:
    world, asking = await _sent_to_the_sender()

    await _replied(
        world,
        asking,
        "Description :- Vets",
        _VETS,
        sender='"tanisha@example.com" <mallory@example.com>',
    )

    chat = await _chat(world, THREAD)
    assert not [one for one in chat.messages if one.text.startswith("A reply")]
