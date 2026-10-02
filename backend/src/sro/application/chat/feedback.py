"""Keeping what went wrong in a chat, for a person to review (`domain.chat.feedback`).

Nothing here decides anything or costs a model call, and nothing here may break or hold up a
chat turn: a row that cannot be kept is logged and the turn goes on. One row per (message, kind).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.chat.brain_turn import BrainReply
from sro.domain.chat.feedback import (
    BUDGET,
    DISAGREEMENT,
    GUARD_REFUSAL,
    RUN_FAILED,
    UNDO,
    Feedback,
    brain_category,
    chain_category,
    kept,
    said_of,
)
from sro.domain.chat.thread import Message, Speaker
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.prompts.chat_brain import CHAT_BRAIN
from sro.domain.shared.identifiers import PrincipalId

logger = logging.getLogger(__name__)

# A run the brain started is under an offer named for the message it answered (`chat:<message>`,
# then `:<hash>` when the turn started it with no offer standing).
FROM_THE_BRAIN = "chat:"

FAILED = frozenset({"failed", "aborted"})


def _brain_started(run: WorkflowRun) -> str:
    """The message a run the brain started answered, or "" for any other run."""
    offer = run.offer or ""
    return offer.split(":")[1] if offer.startswith(FROM_THE_BRAIN) else ""


def _prompt() -> str:
    return f"{CHAT_BRAIN.name} v{CHAT_BRAIN.version}"


class RecordFeedback:
    def __init__(self, uow: UnitOfWork, ids: IdFactory, clock: Clock) -> None:
        self._uow, self._ids, self._clock = uow, ids, clock

    async def turn(
        self,
        ctx: RequestContext,
        *,
        thread_id: str,
        operator: Message,
        reply: BrainReply,
        mode: str,
        chain: Message | None = None,
    ) -> None:
        """What a brain turn got wrong by itself (a guard refused it, it ran out of budget)
        and, in shadow, where it and the old chain's reply `chain` differ in kind."""
        brain: dict[str, object] = {
            "mode": mode,
            "prompt": _prompt(),
            "tools": [
                {
                    "tool": call.tool,
                    "args": kept(call.args),
                    "ok": result.ok,
                    "error": kept(result.error),
                }
                for call, result in reply.steps
            ],
            "reply": said_of(reply.said),
            "category": brain_category(reply.steps),
        }
        refused = next((result for _, result in reply.steps if result.guard), None)
        if refused is not None:
            await self._keep(
                ctx, GUARD_REFUSAL, thread_id, operator, brain, {"refusal": kept(refused.error)}
            )
        if reply.trouble:
            await self._keep(
                ctx, BUDGET, thread_id, operator, brain, {"trouble": list(reply.trouble)}
            )
        if mode == "shadow":
            theirs = chain_category(chain.decision or {}) if chain is not None else "none"
            if theirs != brain["category"]:
                other = {"category": theirs, "reply": said_of(chain.text) if chain else ""}
                await self._keep(ctx, DISAGREEMENT, thread_id, operator, brain, other)

    async def mail_disagreement(
        self,
        ctx: RequestContext,
        message_id: str,
        said: str,
        *,
        chain: Mapping[str, object] | None,
        brain: Mapping[str, object] | None,
    ) -> None:
        """A mail the matcher and the brain (shadow) read differently."""
        try:
            await self._add(
                ctx,
                DISAGREEMENT,
                "",
                message_id,
                said,
                {"mode": "shadow", "read": kept(brain)},
                {"read": kept(chain)},
            )
        except Exception:
            logger.exception("feedback (%s) could not be kept", DISAGREEMENT)

    async def undone(self, ctx: RequestContext, run: WorkflowRun, by: WorkflowRun) -> None:
        """The operator took back `run`: a signal when the brain had started it."""
        await self._of_a_run(
            ctx,
            run,
            UNDO,
            {"undone_by": by.id, "undo_job": by.workflow_id},
        )

    async def failed(self, ctx: RequestContext, run: WorkflowRun, why: str) -> None:
        """A run ended failed or aborted: a signal when the brain had started it."""
        if run.outcome in FAILED:
            await self._of_a_run(
                ctx, run, RUN_FAILED, {"run": run.id, "state": run.outcome, "reason": kept(why)}
            )

    async def _of_a_run(
        self, ctx: RequestContext, run: WorkflowRun, kind: str, other: Mapping[str, object]
    ) -> None:
        try:
            message_id = _brain_started(run)
            if not message_id:
                return
            async with self._uow as uow:
                thread = await uow.threads.holding(
                    ctx.tenant_id,
                    opened_by=PrincipalId(run.started_by or ctx.principal_id.value),
                    message_id=message_id,
                )
            said = next(
                (m for m in (thread.messages if thread else ()) if m.id.value == message_id), None
            )
            started = {
                "mode": "live",
                "prompt": _prompt(),
                "started": {"run": run.id, "job": run.workflow_id, "values": kept(run.values)},
            }
            await self._add(
                ctx,
                kind,
                thread.id.value if thread else "",
                message_id,
                said.text if said and said.speaker is Speaker.OPERATOR else "",
                started,
                other,
            )
        except Exception:
            logger.exception("feedback (%s) could not be kept", kind)

    async def _keep(
        self,
        ctx: RequestContext,
        kind: str,
        thread_id: str,
        operator: Message,
        brain: Mapping[str, object],
        other: Mapping[str, object],
    ) -> None:
        try:
            await self._add(ctx, kind, thread_id, operator.id.value, operator.text, brain, other)
        except Exception:
            logger.exception("feedback (%s) could not be kept", kind)

    async def _add(
        self,
        ctx: RequestContext,
        kind: str,
        thread_id: str,
        message_id: str,
        said: str,
        brain: Mapping[str, object],
        other: Mapping[str, object],
    ) -> None:
        row = Feedback(
            id=f"fbk_{self._ids.new_run_id().value.split('_', 1)[-1]}",
            tenant=ctx.tenant_id.value,
            operator=ctx.principal_id.value,
            thread_id=thread_id,
            message_id=message_id,
            kind=kind,
            created_at=self._clock.now(),
            said=said_of(said),
            brain=dict(brain),
            other=dict(other),
        )
        async with self._uow as uow:
            if await uow.chat_feedback.add(row):
                await uow.commit()
