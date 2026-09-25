from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import replace

from sro.application.execution.plan_step import replay_without_asking
from sro.application.ports.http import HttpCaller, MalformedRequest
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.step import Held, LaneContext, Stopped
from sro.domain.execution.belts import (
    carries_every,
    confirming_read,
    expected_statuses,
    record_carrying,
)
from sro.domain.execution.evidence import recorded_call
from sro.domain.execution.lanes import (
    Lane,
    SeenCall,
    StepResult,
    Verdict,
    fingerprint_of,
    write_confirmed,
)
from sro.domain.execution.records import made_by
from sro.domain.execution.write_plan import seen_values
from sro.domain.observation.trim import path_shape
from sro.domain.shared.hosts import REDACTED
from sro.domain.skill.workflow import Step

K_AUTH_REFUSED = frozenset({401, 403, 419})


class ApiLane:
    lane = Lane.API

    def __init__(self, http: HttpCaller, broker: SessionBroker) -> None:
        self._http = http
        self._broker = broker

    async def execute(self, step: Step, values: Mapping[str, str], ctx: LaneContext) -> StepResult:
        cited = [ctx.by_id[one] for one in step.cites if one in ctx.by_id]
        planned = replay_without_asking(
            step=step,
            cited=cited,
            values=values,
            verified_writes=ctx.ledger,
            seen=seen_values(ctx.workflow),
        )
        recorded = recorded_call(step, ctx.by_id)
        if planned is None or recorded is None or ctx.held is None:
            return StepResult(
                "failed",
                Lane.API,
                "no verified replay for this step",
                never_left=True,
                fingerprint=fingerprint_of(Lane.API, "no_replay"),
            )
        payload = planned.payload
        method, url = str(payload["method"]), str(payload["url"])
        body = payload.get("body")
        recorded_headers = payload.get("headers")
        headers = await self._headers(
            ctx, ctx.held, url, recorded_headers if isinstance(recorded_headers, dict) else {}
        )
        ctx.check_stop()
        await ctx.about_to_write()
        try:
            answered = await self._http.send(
                method, url, headers=headers, body=body if isinstance(body, str) else None
            )
        except MalformedRequest as wrong:
            return StepResult(
                "failed",
                Lane.API,
                f"the call could not be built: {wrong}",
                never_left=True,
                fingerprint=fingerprint_of(Lane.API, "malformed", path_shape(url)),
            )
        except (Stopped, asyncio.CancelledError):
            raise
        except Exception as lost:
            return StepResult("unknown", Lane.API, f"the call may have arrived: {lost}")
        status = answered.status_code
        if status in K_AUTH_REFUSED:
            return StepResult(
                "failed", Lane.API, f"the session was refused ({status})", expired=True
            )
        verdict = write_confirmed(
            recorded=replace(recorded, url=url),
            wanted=expected_statuses(step, ctx.by_id),
            calls=[SeenCall(method, url, status)],
        )
        if verdict == "failed":
            return StepResult(
                "failed",
                Lane.API,
                f"the system answered {status}",
                fingerprint=fingerprint_of(Lane.API, str(status), path_shape(url)),
            )
        made = made_by({"status": status, "body": answered.text})
        if verdict != "done":
            return StepResult("unknown", Lane.API, f"the system answered {status}", read=made)
        try:
            confirmed = await self._confirmed(
                step, planned.confirm or values, ctx, ctx.held, in_slot=bool(planned.confirm)
            )
        except (Stopped, asyncio.CancelledError):
            raise
        except Exception as lost:
            return StepResult("unknown", Lane.API, f"the read-back was lost: {lost}", read=made)
        if not confirmed:
            return StepResult(
                "unknown", Lane.API, "no read-back shows the values written", read=made
            )
        return StepResult("done", Lane.API, "a read-back shows the values written", read=made)

    async def read_back(
        self, step: Step, values: Mapping[str, str], ctx: LaneContext
    ) -> Verdict | None:
        if ctx.held is None:
            return None
        return "done" if await self._confirmed(step, values, ctx, ctx.held) else None

    async def _confirmed(
        self,
        step: Step,
        values: Mapping[str, str],
        ctx: LaneContext,
        held: Held,
        *,
        in_slot: bool = False,
    ) -> bool:
        probe = confirming_read(step, ctx.by_id)
        if probe is None or REDACTED in probe.url:
            return False
        wanted = {name: value for name, value in values.items() if value and value not in probe.url}
        if not wanted:
            return False
        got = await self._http.send(
            "GET", probe.url, headers=await self._headers(ctx, held, probe.url, {})
        )
        if not got.succeeded:
            return False
        if in_slot:
            return record_carrying(got.text, wanted) is not None
        return carries_every(got.text, wanted)

    async def _headers(
        self, ctx: LaneContext, held: Held, url: str, recorded: Mapping[str, object]
    ) -> dict[str, str]:
        said = await self._broker.headers(ctx.ctx, held, url)
        named = {name.lower() for name in said}
        return {
            **{name: str(value) for name, value in recorded.items() if name.lower() not in named},
            **said,
        }
