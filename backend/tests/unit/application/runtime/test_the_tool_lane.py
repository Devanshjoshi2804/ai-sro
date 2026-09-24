from __future__ import annotations

import asyncio

import pytest

from sro.application.execution.mail_job import MailHand, Written
from sro.application.runtime.step import Stopped
from sro.application.runtime.tool_lane import ToolLane
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.runtime_support import _answer, _sent, lane_context, mail_send_step, write_ok


async def write_unwritten(workflow: Workflow, values: object, thread: str) -> Written | str:
    return "no addressee found"


async def test_a_step_that_sends_nothing_never_left() -> None:
    lane = ToolLane(lambda ctx: MailHand(write=write_ok, send=lambda m: _sent([], m, "msg-1")))
    step = Step(order=0, says="Look at the mailbox", system=None, cites=[])

    result = await lane.execute(step, {}, lane_context({}, held=None))

    assert (result.verdict, result.never_left) == ("failed", True)


async def test_an_unwritten_mail_never_left() -> None:
    lane = ToolLane(
        lambda ctx: MailHand(write=write_unwritten, send=lambda m: _sent([], m, "msg-1"))
    )
    step, by_id = mail_send_step()

    result = await lane.execute(step, {}, lane_context(by_id, held=None))

    assert (result.verdict, result.never_left) == ("failed", True)


async def test_send_raising_is_unknown_and_may_have_sent() -> None:
    def send(mail: Written) -> object:
        raise RuntimeError("connector timed out")

    lane = ToolLane(lambda ctx: MailHand(write=write_ok, send=send))
    step, by_id = mail_send_step()

    result = await lane.execute(step, {}, lane_context(by_id, held=None))

    assert (result.verdict, result.lane, result.never_left) == ("unknown", result.lane, False)
    assert "connector timed out" in result.reason


async def test_send_raising_stopped_propagates() -> None:
    async def send(mail: Written) -> object:
        raise Stopped("stopped by the operator")

    lane = ToolLane(lambda ctx: MailHand(write=write_ok, send=send))
    step, by_id = mail_send_step()

    with pytest.raises(Stopped):
        await lane.execute(step, {}, lane_context(by_id, held=None))


async def test_send_raising_cancelled_propagates() -> None:
    async def send(mail: Written) -> object:
        raise asyncio.CancelledError()

    lane = ToolLane(lambda ctx: MailHand(write=write_ok, send=send))
    step, by_id = mail_send_step()

    with pytest.raises(asyncio.CancelledError):
        await lane.execute(step, {}, lane_context(by_id, held=None))


async def test_a_send_step_is_one_connector_call_and_no_tab() -> None:
    sent: list[Written] = []
    lane = ToolLane(lambda ctx: MailHand(write=write_ok, send=lambda m: _sent(sent, m, "msg-1")))
    step, by_id = mail_send_step()

    ctx = lane_context(by_id, held=None, thread="t-1")
    result = await lane.execute(step, {"Order": "42"}, ctx)

    assert (result.verdict, dict(result.read)) == ("done", {"message": "msg-1"})
    assert [one.thread for one in sent] == ["t-1"]


async def test_a_send_that_answered_no_id_is_never_sent_again_blindly() -> None:
    def send(mail: Written) -> object:
        return _answer("", "Gmail did not say")

    lane = ToolLane(lambda ctx: MailHand(write=write_ok, send=send))
    step, by_id = mail_send_step()

    result = await lane.execute(step, {}, lane_context(by_id, held=None))

    assert (result.verdict, result.never_left) == ("unknown", False)
