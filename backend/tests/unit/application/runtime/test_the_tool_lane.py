from __future__ import annotations

from sro.application.execution.mail_job import MailHand, Written
from sro.application.runtime.tool_lane import ToolLane
from tests.unit.runtime_support import _answer, _sent, lane_context, mail_send_step, write_ok


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

    assert result.verdict == "unknown"
