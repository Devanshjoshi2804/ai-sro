"""Say something to the system, and get back what it worked out.

The reply is never improvised. It is a rendering of a `Resolution`: the skill
that was matched and what it still needs, the choice between two that were too
close, or what the knowledge base knows about a task nobody has taught. The
prose exists so an operator can read it; the decision is stored beside it so an
auditor does not have to.

**Nothing is performed here.** A matched skill is offered, and starting it is a
separate request the operator makes — which is what makes their confirmation
the authorisation an assisted run records.
"""

from __future__ import annotations

import logging

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest
from sro.application.intent.match import writes
from sro.application.intent.resolve import Resolution, ResolveIntent
from sro.application.ports.http import TargetUnreachable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.chat.thread import Message, Speaker, Thread, ThreadId
from sro.domain.execution.run import Run, RunStatus
from sro.domain.shared.errors import DomainError

logger = logging.getLogger(__name__)


class StartThread:
    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids

    async def execute(self, ctx: RequestContext) -> Thread:
        thread = Thread(
            id=self._ids.new_thread_id(),
            tenant_id=ctx.tenant_id,
            opened_by=ctx.principal_id,
            opened_at=self._clock.now(),
        )
        async with self._uow as uow:
            await uow.threads.add(thread)
            await uow.commit()
        return thread


class Converse:
    def __init__(
        self,
        uow: UnitOfWork,
        resolver: ResolveIntent,
        clock: Clock,
        ids: IdFactory,
        execute: ExecuteSkill | None = None,
    ) -> None:
        self._uow = uow
        self._resolver = resolver
        self._clock = clock
        self._ids = ids
        self._execute = execute

    async def note(self, ctx: RequestContext, *, thread_id: ThreadId, text: str) -> None:
        """Write something into the thread that nobody asked a question for.

        A pursuit finishes minutes after the request that started it, in a
        background task, and its progress lives only in this process. What it
        did has to end up somewhere an operator can read tomorrow.
        """
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=text,
                    said_at=self._clock.now(),
                )
            )
            await uow.threads.save(thread)
            await uow.commit()

    async def execute(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        text: str,
        system: str | None = None,
        parameters: dict[str, str] | None = None,
    ) -> Thread:
        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)

        resolution = await self._resolver.execute(
            ctx,
            utterance=text,
            system=system,
            # Values already given for the skill under discussion. An operator
            # who answers one question at a time should not lose the first
            # answer when they give the second.
            parameters={**_gathered(thread), **(parameters or {})},
            # What was being talked about a moment ago. A conversation whose
            # every sentence is resolved alone is not a conversation.
            after=_last_asked(thread),
            pinned=_awaiting(thread),
        )

        # A question is answered from the system, now. The taught skill knows
        # which call answers it; what it saw when it was taught is a description
        # of that afternoon, and showing it as though it were current is how a
        # console tells somebody there are sixteen when there are twenty-three.
        #
        # Only reads, and only when nothing is missing. A write still waits for
        # the operator to say go -- that confirmation is what an assisted run
        # records as its authorisation, and it is not ours to assume.
        run = await self._answer_now(ctx, resolution)

        async with self._uow as uow:
            thread = await uow.threads.get(ctx.tenant_id, thread_id)
            now = self._clock.now()
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.OPERATOR,
                    text=text,
                    said_at=now,
                )
            )
            thread.say(
                Message(
                    id=self._ids.new_message_id(),
                    speaker=Speaker.ASSISTANT,
                    text=_reply(resolution) + _why_it_failed(run),
                    said_at=self._clock.now(),
                    decision=_decision(resolution, run),
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread

    async def _answer_now(self, ctx: RequestContext, resolution: Resolution) -> Run | None:
        """Run a read the moment it is asked for, and answer with what came back."""
        matched = resolution.matched
        if self._execute is None or matched is None:
            return None
        if resolution.missing_parameters or not resolution.runnable:
            return None
        if writes(matched.version):
            return None

        try:
            return await self._execute.execute(
                ctx,
                ExecutionRequest(
                    skill_id=matched.skill.id,
                    parameters=dict(resolution.items[0]) if resolution.items else {},
                    version=matched.version.version,
                ),
            )
        except (DomainError, TargetUnreachable) as refusal:
            # A refused read is worth saying out loud, and worth saying in the
            # reply rather than as an empty answer: the breaker being open is a
            # fact about the system, not an absence of transport modes.
            logger.info("could not answer from the system: %s", refusal)
            return None


def _why_it_failed(run: Run | None) -> str:
    """Say what actually went wrong, in the words of the thing that went wrong.

    "1 step did not satisfy their post-conditions" is true of a skill that has
    drifted, a system that is down, and a session that has expired, and those
    want three different people to do three different things. The step already
    knows which; it was just not being read.
    """
    if run is None or run.status is not RunStatus.FAILED:
        return ""
    for step in run.steps:
        if step.detail and "login page" in step.detail:
            return (
                " The connection is signed out — the system answered with its login page. "
                "Sign in once and ask again."
            )
        if step.detail and "no live value" in step.detail:
            return " The session is missing something the system signs its calls with."
    return ""


def _reply(resolution: Resolution) -> str:
    """What to say. Every branch says what happens next, because a reply that
    only reports a state leaves the operator to guess at the next move."""
    if resolution.matched is not None:
        skill = resolution.matched.skill.name
        version = resolution.matched.version
        if resolution.items:
            n = len(resolution.items)
            return (
                f"{skill} does that. Here {'is' if n == 1 else 'are'} the {n} "
                f"{'item' if n == 1 else 'items'} I read from that — check them and "
                "say go."
            )
        if resolution.note:
            return f"{resolution.question or ''} {resolution.note}".strip()
        if resolution.question:
            return f"{resolution.question}"
        return (
            f"{skill} v{version.version} does that — {version.summary} "
            f"Say the word and I will run it."
        )
    if resolution.choices:
        return resolution.question or "More than one skill fits that."
    if resolution.proposal is not None:
        lines = "\n".join(f"· {step.what}" for step in resolution.proposal.steps[:5])
        return f"{resolution.question}\n\n{lines}\n\n{resolution.proposal.caveat}"
    return resolution.question or "I do not know how to do that yet."


def _decision(resolution: Resolution, run: Run | None = None) -> dict[str, object]:
    """The structured half of the reply, kept for the audit trail."""
    return {
        "matched_skill_id": (resolution.matched.skill.id.value if resolution.matched else None),
        "matched_version": (resolution.matched.version.version if resolution.matched else None),
        "confident": resolution.confident,
        "runnable": resolution.runnable,
        "missing_parameters": list(resolution.missing_parameters),
        "why": list(resolution.why),
        "choices": [c.skill.id.value for c in resolution.choices],
        # The table the operator confirms. Rendered rather than acted on: their
        # confirmation is what an assisted run records as its authorisation.
        "items": [dict(item) for item in resolution.items],
        "note": resolution.note,
        "proposal_sources": (list(resolution.proposal.sources) if resolution.proposal else []),
        # The answer, from the system, at the moment it was asked.
        "run_id": run.id.value if run else None,
        # The name, not only the id: a sidebar reading "ran skl_a6f7b33c" tells
        # nobody anything.
        "matched_skill_name": resolution.matched.skill.name if resolution.matched else None,
    }


def _last_asked(thread: Thread) -> str | None:
    """The operator's previous sentence, which is where a follow-up's subject is.

    Theirs rather than the assistant's: the reply is full of words the system
    chose, and letting those steer the next match would have the console
    talking to itself.
    """
    for message in reversed(thread.messages):
        if message.speaker is Speaker.OPERATOR:
            return message.text
    return None


def _awaiting(thread: Thread) -> str | None:
    """The skill the last reply asked for values for, if it is still waiting."""
    for message in reversed(thread.messages):
        if message.speaker is not Speaker.ASSISTANT or not message.decision:
            continue
        decision = message.decision
        if decision.get("missing_parameters"):
            matched = decision.get("matched_skill_id")
            return str(matched) if matched else None
        return None
    return None


def _gathered(thread: Thread) -> dict[str, str]:
    """Every value established so far for the skill under discussion.

    Read back off the decisions rather than held in memory: the thread is what
    survives a restart, and an operator answering three questions over five
    minutes should not depend on a process staying up.
    """
    values: dict[str, str] = {}
    for message in thread.messages:
        items = (message.decision or {}).get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                values.update({str(key): str(value) for key, value in item.items() if value})
    return values
