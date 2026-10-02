from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping

from sro.application.context import RequestContext
from sro.application.execution.mail_job import WHAT_IT_SAYS, MailHand, Unaddressed
from sro.application.runtime.step import LaneContext, NeedsAPerson, Stopped
from sro.domain.chat.asked_by import by_hand
from sro.domain.execution.lanes import Lane, StepResult
from sro.domain.execution.mail_job import MAIL_BODY, sends_mail
from sro.domain.skill.workflow import Step


class ToolLane:
    lane = Lane.TOOL

    def __init__(self, hand: Callable[[RequestContext], MailHand]) -> None:
        self._hand = hand

    async def execute(self, step: Step, values: Mapping[str, str], ctx: LaneContext) -> StepResult:
        if not sends_mail(step, ctx.by_id) and by_hand(ctx.workflow, step, ctx.by_id):
            raise NeedsAPerson(
                f"'{step.says}' changes your mailbox in a way the mail tool cannot: do it in "
                "your mailbox, then say whether it was done",
                kind="step",
            )
        if not sends_mail(step, ctx.by_id):
            return StepResult(
                "failed", Lane.TOOL, "this mailbox step sends nothing", never_left=True
            )
        hand = self._hand(ctx.ctx)
        written = await hand.write(ctx.workflow, values, ctx.thread, ctx.by_id, ctx.request)
        if isinstance(written, Unaddressed):
            raise NeedsAPerson(str(written), kind="recipient")
        if isinstance(written, str):
            raise NeedsAPerson(f"{written}. {WHAT_IT_SAYS}", kind=MAIL_BODY)
        ctx.check_stop()
        await ctx.about_to_write(self.lane)
        try:
            sent_id, why = await hand.send(written)
        except (Stopped, asyncio.CancelledError):
            raise
        except Exception as exc:
            return StepResult("unknown", Lane.TOOL, str(exc))
        if not sent_id:
            return StepResult("unknown", Lane.TOOL, why)
        return StepResult(
            "done",
            Lane.TOOL,
            f"The mailbox took the mail to {written.to}",
            read={"message": sent_id},
        )
