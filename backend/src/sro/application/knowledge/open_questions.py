"""What the system does when it does not know, instead of choosing.

Two endpoints answered "how many transport modes": the site's view said sixteen
and the wider collection said twenty-three. Both were real, both had been
observed, and the system picked the first one it happened to see -- so it gave a
confident answer to a question it had not understood, and the operator found out
by counting rows on a screen.

Picking was the mistake, not picking wrongly. The failure mode this system is
arranged against is a confident wrong action, and an ambiguity resolved by
whichever evidence arrived first is exactly that with extra steps.

So ambiguity is written down as a question, kept beside what is known about the
system, and asked once. The answer is knowledge like any other: it supersedes
the question, it carries who said it, and every later decision reads it instead
of guessing again. A system that asks the same thing twice has not learned
anything; a system that never asks has only hidden what it does not know.

The shape is deliberately general. Anything that finds itself choosing between
plausible readings -- which collection an entity lives in, which of two screens
does a task, whether a field is an input or a constant -- records a question
here rather than inventing a rule, and the operator's answer is what settles it
for everybody afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.knowledge.record_claim import Claim, RecordClaims
from sro.application.ports.repositories import UnitOfWork
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry


@dataclass(frozen=True, slots=True)
class Ambiguity:
    """Two or more readings of one thing, none of which may be assumed."""

    system: str
    key: str
    """What is ambiguous, addressed the same way twice so asking again finds
    the answer rather than asking again."""

    question: str
    options: tuple[str, ...]
    because: tuple[str, ...] = ()
    """The evidence for each reading. An operator choosing between two endpoint
    names needs to know one returned sixteen rows and the other twenty-three."""


class AskAbout:
    """Record what could not be decided, and let it be decided once."""

    def __init__(self, uow: UnitOfWork, record: RecordClaims) -> None:
        self._uow = uow
        self._record = record

    async def raise_question(self, ctx: RequestContext, ambiguity: Ambiguity) -> None:
        """Write the question down. Idempotent: the same ambiguity found twice
        is one question, and an answered one is never re-asked."""
        async with self._uow as uow:
            existing = await uow.knowledge.search(
                ctx.tenant_id, terms=ambiguity.key, kinds=(EntryKind.QUESTION,), limit=5
            )
        if any(entry.key == ambiguity.key for entry in existing):
            return

        await self._record.execute(
            ctx,
            (
                Claim(
                    system=ambiguity.system,
                    kind=EntryKind.QUESTION,
                    key=ambiguity.key,
                    title=ambiguity.question,
                    body={
                        "question": ambiguity.question,
                        "options": list(ambiguity.options),
                        "because": list(ambiguity.because),
                    },
                    source="ambiguity",
                    # Asserted, and deliberately the weakest level: a question is
                    # not evidence about the system, it is evidence that nobody
                    # has said yet.
                    evidence=EvidenceLevel.ASSERTED,
                ),
            ),
        )

    async def answer(
        self, ctx: RequestContext, *, system: str, key: str, chosen: str, by: str
    ) -> None:
        """Settle it, for everybody, permanently.

        Recorded as ``observed`` rather than asserted: somebody who works here
        looked at both readings and said which one their words mean, which is a
        stronger thing than a catalogue's opinion and supersedes the question.
        """
        await self._record.execute(
            ctx,
            (
                Claim(
                    system=system,
                    kind=EntryKind.QUESTION,
                    key=key,
                    title=f"{key}: {chosen}",
                    body={"answer": chosen, "answered_by": by},
                    source=f"operator:{by}",
                    evidence=EvidenceLevel.OBSERVED,
                ),
            ),
        )

    async def settled(self, ctx: RequestContext, *, key: str) -> str | None:
        """What was decided about this, if anybody has decided it."""
        async with self._uow as uow:
            found = await uow.knowledge.search(
                ctx.tenant_id, terms=key, kinds=(EntryKind.QUESTION,), limit=10
            )
        for entry in found:
            if entry.key == key and entry.current:
                answer = entry.body.get("answer")
                if isinstance(answer, str):
                    return answer
        return None

    async def outstanding(self, ctx: RequestContext) -> tuple[KnowledgeEntry, ...]:
        """Everything the system knows it does not know.

        Worth a screen of its own: these are the places where the next confident
        answer would be a guess, and they are cheap to settle while somebody
        remembers the context.
        """
        async with self._uow as uow:
            found = await uow.knowledge.search(
                ctx.tenant_id, kinds=(EntryKind.QUESTION,), limit=200
            )
        return tuple(entry for entry in found if entry.current and "answer" not in entry.body)
