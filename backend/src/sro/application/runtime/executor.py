from __future__ import annotations

import asyncio
from collections.abc import Collection, Mapping
from dataclasses import replace

from sro.application.ports.locks import AccountBusy
from sro.application.ports.page import PageGone
from sro.application.runtime.api_lane import replay_of
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.step import (
    LaneContext,
    NeedsAPerson,
    ReadsBack,
    StepLane,
    Stopped,
)
from sro.domain.chat.asked_by import only_reads_the_mail
from sro.domain.execution.evidence import primary_gesture
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
        if only_reads_the_mail(step, ctx.by_id):
            return (StepResult("read", Lane.TOOL, "the mail this run came from is already read"),)
        tool = sends_mail(step, ctx.by_id)
        adding = ctx.adding.get(step.order)
        slotted = set(learned_slots(ctx.workflow, step))
        added_ok = adding is None or (not adding.fresh and set(adding.known.values()) <= slotted)
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
        return tuple(tried)

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
        )
