from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping

from sro.application.context import RequestContext
from sro.application.execution.mail_job import MailHand
from sro.application.runtime.step import LaneContext, Stopped
from sro.domain.execution.lanes import Lane, StepResult, fingerprint_of
from sro.domain.execution.mail_job import sends_mail
from sro.domain.skill.workflow import Step


class ToolLane:
    lane = Lane.TOOL

    def __init__(self, hand: Callable[[RequestContext], MailHand]) -> None:
        self._hand = hand

    async def execute(self, step: Step, values: Mapping[str, str], ctx: LaneContext) -> StepResult:
        if not sends_mail(step, ctx.by_id):
            return StepResult(
                "failed", Lane.TOOL, "this mailbox step sends nothing", never_left=True
            )
        hand = self._hand(ctx.ctx)
        written = await hand.write(ctx.workflow, values, ctx.thread)
        if isinstance(written, str):
            return StepResult(
                "failed",
                Lane.TOOL,
                written,
                never_left=True,
                fingerprint=fingerprint_of(Lane.TOOL, "unwritten"),
            )
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
            "done", Lane.TOOL, f"Gmail took the mail to {written.to}", read={"message": sent_id}
        )
