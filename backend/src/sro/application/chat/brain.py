"""The loop: one model, the tools, and the guards that live here, not in the model.

Each turn asks the model for one next action. A call runs a tool and its result
goes back fenced as data; a say ends the turn. At most K_BRAIN_STEPS tool steps,
the tenant's cost cap before every ask, and when the model cannot answer the
reply says so and starts nothing.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from sro.application.chat.brain_tools import Tool, described
from sro.application.context import RequestContext
from sro.application.intent.spend import over_cap
from sro.application.ports.model import Asker, AskerUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.shared.asking import ask
from sro.application.shared.refusals import OverCap
from sro.domain.chat.brain_turn import BrainReply, ToolCall, ToolResult, fenced_result, step_of
from sro.domain.prompts.chat_brain import CHAT_BRAIN
from sro.domain.recording.sensitivity import is_secret_field

logger = logging.getLogger(__name__)

K_BRAIN_STEPS = 5

K_HISTORY = 12

K_LOGGED = 300

# Shadow mode runs these and only these; everything else is recorded as "would".
READ_ONLY = frozenset({"find_jobs", "run_status", "check_mail", "lookup"})


@dataclass(frozen=True)
class Origin:
    kind: Literal["chat", "mail"]
    sender: str = ""
    subject: str = ""


def _without_secrets(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            k: "<secret>" if is_secret_field(str(k)) else _without_secrets(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_without_secrets(one) for one in value]
    return value


def _cannot(
    why: str, decisions: list[dict[str, object]], steps: list[tuple[ToolCall, ToolResult]]
) -> BrainReply:
    # What the turn already did stays on the record: a run it started is still a run.
    return BrainReply(f"I can't answer right now: {why}.", tuple(decisions), tuple(steps))


class Brain:
    def __init__(
        self,
        uow: UnitOfWork,
        asker: Asker,
        clock: Clock,
        tools: Sequence[Tool],
        *,
        cap_usd: float,
    ) -> None:
        self._uow, self._asker, self._clock, self._cap_usd = uow, asker, clock, cap_usd
        self._tools = {one.name: one for one in tools}

    async def turn(
        self,
        ctx: RequestContext,
        *,
        message: str,
        history: Sequence[str],
        origin: Origin,
        asking: str = "",
        page: str = "",
        dry: bool = False,
    ) -> BrainReply:
        trusted: dict[str, object] = {
            "origin": origin.kind,
            "asking": asking,
            "page": page,
            "tools": described(list(self._tools.values())),
        }
        untrusted = {"message": message, "history": "\n".join(history[-K_HISTORY:])}
        if origin.kind == "mail":
            untrusted |= {"mail from": origin.sender, "mail subject": origin.subject}
        if (status := self._tools.get("run_status")) is not None:
            # Run values can come from a mail, so the runs are data like the rest.
            runs = await status.run(ctx, {})
            untrusted["recent runs"] = json.dumps(runs.data, ensure_ascii=False, default=str)
        results: list[str] = []
        steps: list[tuple[ToolCall, ToolResult]] = []
        decisions: list[dict[str, object]] = []
        started: set[str] = set()
        for _ in range(K_BRAIN_STEPS):
            async with self._uow as uow:
                why = await over_cap(
                    uow, ctx.tenant_id, now=self._clock.now(), cap_usd=self._cap_usd
                )
            if why is not None:
                return _cannot(why, decisions, steps)
            try:
                answer = await ask(
                    self._asker,
                    CHAT_BRAIN,
                    trusted=trusted,
                    untrusted={**untrusted, "results": "\n".join(results)},
                )
            except (OverCap, AskerUnavailable) as refused:
                return _cannot(str(refused), decisions, steps)
            if answer.data is None:
                return _cannot(answer.error or "the model did not answer", decisions, steps)
            step = step_of(answer.data)
            if step.say is not None:
                return BrainReply(step.say, tuple(decisions), tuple(steps))
            if step.call is None:
                results.append(
                    fenced_result(
                        ToolCall("answer", {}),
                        ToolResult(False, error="that is not a usable action: call a tool or say"),
                    )
                )
                continue
            call = step.call
            begun = time.monotonic()
            result = await self._run(ctx, call, dry=dry, started=started)
            logger.info(
                "brain step: tool=%s args=%s ok=%s error=%s latency=%.3fs cost=%s",
                call.tool,
                json.dumps(_without_secrets(call.args), ensure_ascii=False, default=str)[:K_LOGGED],
                result.ok,
                result.error[:K_LOGGED],
                time.monotonic() - begun,
                answer.cost_usd if not answer.unpriced else "unknown",
            )
            steps.append((call, result))
            if result.decision is not None:
                decisions.append(result.decision)
            results.append(fenced_result(call, result))
            if result.ends_turn:
                question = str((result.decision or {}).get("question") or "")
                return BrainReply(question, tuple(decisions), tuple(steps))
        did = ", ".join(call.tool for call, _ in steps)
        return BrainReply(
            f"I could not finish that in {K_BRAIN_STEPS} steps; here is what I did: {did}.",
            tuple(decisions),
            tuple(steps),
        )

    async def _run(
        self, ctx: RequestContext, call: ToolCall, *, dry: bool, started: set[str]
    ) -> ToolResult:
        tool = self._tools.get(call.tool)
        if tool is None:
            return ToolResult(False, error=f"no such tool: {call.tool}")
        if dry and call.tool not in READ_ONLY:
            return ToolResult(True, {"would": call.tool})
        if call.tool == "start_job":
            # One start per distinct job and values a turn: a refusal is answered, not retried.
            key = json.dumps(call.args, sort_keys=True, default=str)
            if key in started:
                return ToolResult(False, error="that start was already tried this turn")
            started.add(key)
        return await tool.run(ctx, call.args)
