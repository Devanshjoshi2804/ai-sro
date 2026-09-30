from __future__ import annotations

import asyncio
from collections.abc import Collection, Mapping
from dataclasses import replace

from sro.application.ports.locks import AccountBusy
from sro.application.ports.page import PageGone
from sro.application.runtime.api_lane import confirmed_keys, replay_of
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.step import (
    LaneContext,
    NeedsAPerson,
    ReadsBack,
    StepLane,
    Stopped,
)
from sro.domain.chat.asked_by import by_hand, only_reads_the_mail
from sro.domain.execution.evidence import primary_gesture, writes
from sro.domain.execution.lanes import Broken, Lane, StepResult, lanes_for
from sro.domain.execution.mail_job import sends_mail
from sro.domain.execution.write_plan import learned_slots
from sro.domain.skill.workflow import Step


class StepExecutor:
    def __init__(
        self,
        tool: StepLane,
        api: ReadsBack,
        ui: StepLane,
        sight: StepLane,
        broker: SessionBroker,
    ) -> None:
        self._lanes: dict[Lane, StepLane] = {
            Lane.TOOL: tool,
            Lane.API: api,
            Lane.UI: ui,
            Lane.SIGHT: sight,
        }
        self._api = api
        self._broker = broker

    async def run(
        self,
        step: Step,
        values: Mapping[str, str],
        ctx: LaneContext,
        *,
        broken: Collection[Broken],
        start_url: str,
    ) -> tuple[StepResult, ...]:
        mailbox = by_hand(ctx.workflow, step, ctx.by_id)
        if only_reads_the_mail(step, ctx.by_id) and not mailbox:
            return (StepResult("read", Lane.TOOL, "the mail this run came from is already read"),)
        tool = mailbox or sends_mail(step, ctx.by_id)
        adding = ctx.adding.get(step.order)
        known = set() if adding is None else set(adding.known.values())
        added_ok = adding is None or (
            set(adding.fresh) <= known <= set(learned_slots(ctx.workflow, step))
        )
        api = not tool and added_ok and replay_of(step, values, ctx) is not None
        primary = None if tool else primary_gesture(step, ctx.by_id)
        page = None if primary is None else primary.page_url or primary.url
        tried: list[StepResult] = []
        ladder = lanes_for(
            step.order, tool=tool, api=api, browser=primary is not None, broken=broken
        )
        for lane in ladder:
            result = await self._lanes[lane].execute(step, values, ctx)
            if result.expired and ctx.held is not None:
                back_to = page if lane in (Lane.UI, Lane.SIGHT) else None
                try:
                    await self._broker.reauth(ctx.ctx, ctx.held, start_url, back_to=back_to)
                except (NeedsAPerson, AccountBusy, PageGone) as why:
                    why.tried = (*tried, replace(result, reason=f"{result.reason}; {why}"))
                    raise
                except Stopped:
                    raise
                except Exception as why:
                    failed = f"sign-in failed: {type(why).__name__}"
                    return (*tried, replace(result, reason=failed))
                again = replace(ctx, reauthed=True)
                if result.verdict == "unknown":
                    result = await self._settled(step, values, again, result)
                else:
                    result = await self._lanes[lane].execute(step, values, again)
            tried.append(result)
            if result.verdict != "failed" or result.expired:
                break
        if tried and tried[-1].verdict == "failed" and not tried[-1].expired:
            went = await self._by_its_address(step, ctx, page)
            if went is not None:
                tried.append(went)
        return tuple(tried)

    async def _by_its_address(
        self, step: Step, ctx: LaneContext, page: str | None
    ) -> StepResult | None:
        """A step that writes nothing only moves the browser. When its control is
        not on the page -- the job was recorded from another screen -- the page
        the next step was recorded on is reached by its address instead."""
        if ctx.held is None or writes(step, ctx.by_id):
            return None
        later = [one for one in ctx.workflow.steps if one.order > step.order]
        following = min(later, key=lambda one: one.order, default=None)
        gesture = None if following is None else primary_gesture(following, ctx.by_id)
        there = None if gesture is None else gesture.page_url or gesture.url
        if not there or there == page:
            return None
        await self._broker.go_to(ctx.ctx, ctx.held, there)
        return StepResult("done", Lane.UI, f"its control was not on the page; went to {there}")

    async def _settled(
        self, step: Step, values: Mapping[str, str], ctx: LaneContext, lost: StepResult
    ) -> StepResult:
        try:
            verdict = await self._api.read_back(step, values, ctx)
        except (Stopped, asyncio.CancelledError):
            raise
        except Exception:
            return lost
        if verdict != "done":
            return lost
        return StepResult(
            "done",
            lost.lane,
            "a read-back after signing back in shows the values written",
            read=lost.read,
            keyed=confirmed_keys(step, values, ctx),
            answered=lost.answered,
        )
