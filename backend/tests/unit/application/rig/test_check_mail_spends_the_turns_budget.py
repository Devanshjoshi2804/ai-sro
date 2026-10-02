"""Day-end 4: a chat turn's check_mail reads each mail with a brain turn of its own. Those reads
are the outer turn's spending, drawn from its remaining calls and dollars, not a second budget."""

from __future__ import annotations

from typing import Any, cast

from sro.application.chat.brain import Brain
from sro.application.chat.brain_reader import BrainReader
from sro.application.chat.brain_tools import brain_tools
from sro.application.chat.read_threads import ReadThreads
from sro.application.execution.workflow_runs import GetWorkflowRun, ListWorkflowRuns
from sro.domain.chat.brain_turn import Origin
from sro.domain.shared.prices import Answer
from tests.unit.application.chat.test_brain_tools import _acting
from tests.unit.application.rig.test_from_the_mail import CTX, _found, _look, _Reads
from tests.unit.application.rig.test_the_mail_door_asks_through_the_brain import (
    LIVE,
    _call,
    _mail_json,
    _say,
    _Sends,
)
from tests.unit.fakes import FakeAsker, FakeClock


async def _turn(
    *answers: Answer, max_calls: int = 20, max_usd: float = -1.0
) -> tuple[Brain, FakeAsker]:
    acting = await _acting()
    uow = acting.world.uow
    mailbox = _Sends(
        search=_found("m-1", "m-2"),
        **{
            "m-1": _mail_json("hello", ident="m-1"),
            "m-2": _mail_json("hello again", ident="m-2"),
        },
    )
    asker = FakeAsker(*answers)
    brains: list[Brain] = []
    door = _look(
        uow,
        mailbox,
        _Reads(),
        start=acting.start,
        reader=lambda: BrainReader(brains[0]),
        reader_tenants=LIVE,
    )
    tools = brain_tools(
        uow=uow,
        clock=FakeClock(),
        runs=ListWorkflowRuns(uow),
        run=GetWorkflowRun(uow),
        threads=ReadThreads(uow),
        look_mail=door,
        look_up=cast(Any, None),
        start=acting.start,
        plan=cast(Any, None),
        spawn=lambda coro: coro.close(),
    )
    brains.append(
        Brain(
            uow, asker, FakeClock(), tools, cap_usd=5.0, max_calls=max_calls, max_turn_usd=max_usd
        )
    )
    return brains[0], asker


async def test_the_reads_check_mail_makes_come_out_of_the_turns_call_budget() -> None:
    """Three calls: the outer asks for the look (1), one mail is read (2), and the last call is
    kept back so the outer turn can still say what was done."""
    brain, asker = await _turn(_call("check_mail"), _say("nothing"), _say("done"), max_calls=3)

    reply = await brain.turn(CTX, message="check my mail", history=[], origin=Origin("chat"))

    assert len(asker.asked) == 3, "a read spent the call the outer turn needs to reply"
    assert reply.said == "done"


async def test_the_reads_check_mail_makes_come_out_of_the_turns_dollars() -> None:
    brain, asker = await _turn(
        Answer(data=_call("check_mail").data, cost_usd=0.06),
        Answer(data=_say("nothing").data, cost_usd=0.06),
        _say("done"),
        max_usd=0.15,
    )

    reply = await brain.turn(CTX, message="check my mail", history=[], origin=Origin("chat"))

    assert len(asker.asked) == 3 and reply.said == "done"


async def test_a_mail_the_budget_left_unread_is_read_by_the_next_look() -> None:
    brain, asker = await _turn(
        _call("check_mail"),
        _say("nothing"),
        _say("done"),
        _call("check_mail"),
        _say("nothing"),
        _say("done"),
        max_calls=3,
    )
    await brain.turn(CTX, message="check my mail", history=[], origin=Origin("chat"))
    after_first = len(asker.asked)

    await brain.turn(CTX, message="check again", history=[], origin=Origin("chat"))

    assert after_first == 3 and len(asker.asked) == 6, "the unread mail was lost, not left"
