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

from sro.application.context import RequestContext
from sro.application.intent.resolve import Resolution, ResolveIntent
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.chat.thread import Message, Speaker, Thread, ThreadId


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
        self, uow: UnitOfWork, resolver: ResolveIntent, clock: Clock, ids: IdFactory
    ) -> None:
        self._uow = uow
        self._resolver = resolver
        self._clock = clock
        self._ids = ids

    async def execute(
        self,
        ctx: RequestContext,
        *,
        thread_id: ThreadId,
        text: str,
        system: str | None = None,
        parameters: dict[str, str] | None = None,
    ) -> Thread:
        resolution = await self._resolver.execute(
            ctx, utterance=text, system=system, parameters=parameters
        )

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
                    text=_reply(resolution),
                    said_at=self._clock.now(),
                    decision=_decision(resolution),
                )
            )
            await uow.threads.save(thread)
            await uow.commit()
        return thread


def _reply(resolution: Resolution) -> str:
    """What to say. Every branch says what happens next, because a reply that
    only reports a state leaves the operator to guess at the next move."""
    if resolution.matched is not None:
        skill = resolution.matched.skill.name
        version = resolution.matched.version
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


def _decision(resolution: Resolution) -> dict[str, object]:
    """The structured half of the reply, kept for the audit trail."""
    return {
        "matched_skill_id": (resolution.matched.skill.id.value if resolution.matched else None),
        "matched_version": (resolution.matched.version.version if resolution.matched else None),
        "confident": resolution.confident,
        "runnable": resolution.runnable,
        "missing_parameters": list(resolution.missing_parameters),
        "why": list(resolution.why),
        "choices": [c.skill.id.value for c in resolution.choices],
        "proposal_sources": (list(resolution.proposal.sources) if resolution.proposal else []),
    }
