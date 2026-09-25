from __future__ import annotations

import asyncio
from collections.abc import Collection, Mapping
from dataclasses import replace

from sro.application.runtime.api_lane import replay_of
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.step import LaneContext, ReadsBack, StepLane, Stopped
from sro.domain.chat.asked_by import only_reads_the_mail
from sro.domain.execution.evidence import primary_gesture
from sro.domain.execution.lanes import Broken, Lane, StepResult, lanes_for
from sro.domain.execution.mail_job import sends_mail
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
        api = not tool and replay_of(step, values, ctx) is not None
        browser = not tool and primary_gesture(step, ctx.by_id) is not None
        tried: list[StepResult] = []
        for lane in lanes_for(step.order, tool=tool, api=api, browser=browser, broken=broken):
            result = await self._lanes[lane].execute(step, values, ctx)
            if result.expired and ctx.held is not None:
                await self._broker.reauth(ctx.ctx, ctx.held, start_url)
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
