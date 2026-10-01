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
from datetime import UTC

from sro.application.chat.brain_tools import Checks, Tool, described, start_key
from sro.application.context import RequestContext
from sro.application.intent.spend import over_cap
from sro.application.ports.model import Asker, AskerUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.shared.asking import ask
from sro.application.shared.refusals import OverCap
from sro.domain.chat.brain_turn import (
    K_HISTORY,
    BrainReply,
    Origin,
    ToolCall,
    ToolResult,
    Turn,
    fenced_result,
    step_of,
)
from sro.domain.prompts.chat_brain import CHAT_BRAIN
from sro.domain.recording.sensitivity import is_secret_field, redact_shapes

logger = logging.getLogger(__name__)

K_BRAIN_STEPS = 5

K_LOGGED = 300

# Shadow mode runs these and only these; everything else is recorded as "would". Not
# check_mail: a look in the mailbox starts runs and writes questions, and shadow mode is
# only ever a reading. Not lookup: it takes a Steel session beside the chain's own look and
# its model spend would count against the day's cap.
READ_ONLY = frozenset({"find_jobs", "run_status"})


def _without_secrets(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            k: "<secret>" if is_secret_field(str(k)) else _without_secrets(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_without_secrets(one) for one in value]
    # A secret can sit inside a value whose name is harmless (a mail body, a description).
    return redact_shapes(value) if isinstance(value, str) else value


def _cannot(
    why: str, decisions: list[dict[str, object]], steps: list[tuple[ToolCall, ToolResult]]
) -> BrainReply:
    # What the turn already did stays on the record: a run it started is still a run.
    return BrainReply(f"I can't answer right now: {why}.", tuple(decisions), tuple(steps))


def _stopped(
    decisions: list[dict[str, object]],
    steps: list[tuple[ToolCall, ToolResult]],
    within: str = "within what one message may use",
) -> BrainReply:
    did = ", ".join(call.tool for call, _ in steps)
    return BrainReply(
        f"I could not finish that {within}" + (f"; here is what I did: {did}." if did else "."),
        tuple(decisions),
        tuple(steps),
    )


# `converse._history` prefixes each line with its speaker.
_OPERATOR = "operator: "


class Brain:
    def __init__(
        self,
        uow: UnitOfWork,
        asker: Asker,
        clock: Clock,
        tools: Sequence[Tool],
        *,
        cap_usd: float,
        max_calls: int = K_BRAIN_STEPS + 1,
        max_turn_usd: float = -1.0,
    ) -> None:
        self._uow, self._asker, self._clock, self._cap_usd = uow, asker, clock, cap_usd
        self._max_calls, self._max_turn_usd = max_calls, max_turn_usd
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
        offer: str = "",
        dry: bool = False,
    ) -> BrainReply:
        steps: list[tuple[ToolCall, ToolResult]] = []
        decisions: list[dict[str, object]] = []
        try:
            return await self._turn(
                ctx, message, history, origin, asking, page, offer, dry, steps, decisions
            )
        except Exception:
            # Whatever broke is the log's; the operator is told it plainly, and what the turn
            # already did (a run it started) stays on the record.
            logger.exception("brain turn failed")
            return _cannot("something went wrong", decisions, steps)

    async def _turn(
        self,
        ctx: RequestContext,
        message: str,
        history: Sequence[str],
        origin: Origin,
        asking: str,
        page: str,
        offer: str,
        dry: bool,
        steps: list[tuple[ToolCall, ToolResult]],
        decisions: list[dict[str, object]],
    ) -> BrainReply:
        trusted: dict[str, object] = {
            "origin": origin.kind,
            # No operator timezone is held, so the day is UTC's and says so.
            "today": f"{self._clock.now().astimezone(UTC).date().isoformat()} (UTC)",
            "tools": described(list(self._tools.values())),
        }
        # The open question is built from a mail's words and a page title is anyone's text.
        untrusted = {"message": message, "history": "\n".join(history[-K_HISTORY:])}
        if asking:
            untrusted["asking"] = asking
        if page:
            untrusted["page"] = page
        if origin.kind == "mail":
            untrusted |= {"mail from": origin.sender, "mail subject": origin.subject}
        if (status := self._tools.get("run_status")) is not None:
            # Run values can come from a mail, so the runs are data like the rest.
            runs = await status.run(ctx, {})
            untrusted["recent runs"] = json.dumps(runs.data, ensure_ascii=False, default=str)
        results: list[str] = []
        started: set[str] = set()
        # A value the model gives a tool must be in the operator's words (or the question they
        # answered), never in a tool's result or the assistant's own earlier lines.
        theirs = [
            one.removeprefix(_OPERATOR) for one in history[-K_HISTORY:] if one.startswith(_OPERATOR)
        ]
        turn = Turn(said="\n".join([message, *theirs, asking]), offer=offer)
        calls, spent = 0, 0.0
        for _ in range(K_BRAIN_STEPS):
            if calls >= self._max_calls or 0 <= self._max_turn_usd <= spent:
                return _stopped(decisions, steps)
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
            # A fallback is a second call on the same prompt.
            calls += 2 if answer.fell_back else 1
            spent += answer.cost_usd
            if answer.data is None:
                # The model's own error text is the log's, not the operator's.
                logger.warning("brain: the model did not answer: %s", answer.error)
                return _cannot("the model did not answer", decisions, steps)
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
            result = await self._run(ctx, call, turn, dry=dry, started=started)
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
                return BrainReply(result.said, tuple(decisions), tuple(steps))
        return _stopped(decisions, steps, f"in {K_BRAIN_STEPS} steps")

    async def shadow(
        self,
        ctx: RequestContext,
        *,
        message: str,
        history: Sequence[str],
        origin: Origin,
        asking: str = "",
        page: str = "",
    ) -> None:
        """A dry turn whose only effect is one log line; it never raises."""
        try:
            reply = await self.turn(
                ctx,
                message=message,
                history=history,
                origin=origin,
                asking=asking,
                page=page,
                dry=True,
            )
            start = next((call for call, _ in reply.steps if call.tool == "start_job"), None)
            title = ""
            if start is not None:
                async with self._uow as uow:
                    job = await uow.workflows.get(ctx.tenant_id, str(start.args.get("job_id")))
                title = job.title if job is not None else "an unknown job"
            logger.info(
                "brain shadow: tools=%s would_start=%r said=%r",
                [call.tool for call, _ in reply.steps],
                title,
                reply.said[:K_LOGGED],
            )
        except Exception:
            logger.exception("brain shadow failed")

    async def _run(
        self, ctx: RequestContext, call: ToolCall, turn: Turn, *, dry: bool, started: set[str]
    ) -> ToolResult:
        tool = self._tools.get(call.tool)
        if tool is None:
            return ToolResult(False, error=f"no such tool: {call.tool}")
        if call.unreadable:
            return ToolResult(False, error="args is not a JSON object")
        if dry and call.tool not in READ_ONLY:
            # A refusal is shown as it would be; only the doing is not done.
            if isinstance(tool, Checks) and (refused := await tool.check(ctx, call.args, turn)):
                return refused
            return ToolResult(True, {"would": call.tool})
        if call.tool == "start_job":
            # One start per distinct job and values a turn: a refusal is answered, not retried.
            key = start_key(call.args)
            if key in started:
                return ToolResult(False, error="that start was already tried this turn")
            started.add(key)
        try:
            return await tool.run(ctx, call.args, turn)
        except Exception:
            # A bug or an outage in one tool is that step's failure, not the whole message's.
            logger.exception("brain tool %s failed", call.tool)
            return ToolResult(False, error="that tool failed")
