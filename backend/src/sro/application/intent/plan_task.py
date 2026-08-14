"""What the knowledge base says a task would involve, when nothing was taught.

A proposal is not a skill. It cites screens, endpoints and form models rather
than two demonstrations, so it has no evidence that anybody ever performed it
successfully -- which is exactly the difference `docs/12` draws around generated
workflows. It is shown to an operator, and the honest next move is usually
"teach me this once".

Nothing here is executable. Turning a proposal into something that runs means
giving it provenance, and provenance comes from doing the task, not from reading
about it.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.intent.match import words
from sro.application.knowledge.retrieve import Question, Retrieve
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry

_CANDIDATES = 8


@dataclass(frozen=True, slots=True)
class ProposedStep:
    what: str
    detail: str
    source: str
    evidence: EvidenceLevel


@dataclass(frozen=True, slots=True)
class Proposal:
    steps: tuple[ProposedStep, ...]
    sources: tuple[str, ...]
    caveat: str = (
        "Read from the knowledge base, not from a demonstration. Nobody has "
        "performed this here, so it is a description rather than a skill."
    )


class PlanTask:
    def __init__(self, retrieve: Retrieve) -> None:
        self._retrieve = retrieve

    async def execute(
        self, ctx: RequestContext, *, utterance: str, system: str | None = None
    ) -> Proposal | None:
        asked = words(utterance)
        if not asked:
            return None

        found = await self._retrieve.execute(
            ctx,
            Question(
                text=utterance,
                system=system,
                kinds=(EntryKind.SCREEN, EntryKind.FORM, EntryKind.ENDPOINT, EntryKind.QUIRK),
                limit=_CANDIDATES,
            ),
        )
        if not found:
            return None

        steps = tuple(step for entry in found if (step := _step(entry)) is not None)
        if not steps:
            return None
        return Proposal(steps=steps, sources=tuple(sorted({entry.source for entry in found})))


def _step(entry: KnowledgeEntry) -> ProposedStep | None:
    match entry.kind:
        case EntryKind.SCREEN:
            return ProposedStep(
                what=f"open {entry.title}",
                detail=str(entry.body.get("label") or entry.key),
                source=entry.source,
                evidence=entry.evidence,
            )
        case EntryKind.FORM:
            required = [
                str(field.get("label") or field.get("field"))
                for field in _fields(entry.body.get("required"))
            ]
            return ProposedStep(
                what=f"fill in {entry.body.get('label') or entry.key}",
                detail=("required: " + ", ".join(required)) if required else "no required fields",
                source=entry.source,
                evidence=entry.evidence,
            )
        case EntryKind.ENDPOINT:
            return ProposedStep(
                what=f"the screen calls {entry.key}",
                detail=f"{entry.body.get('service', '')} {entry.body.get('kind', '')}".strip(),
                source=entry.source,
                evidence=entry.evidence,
            )
        case EntryKind.QUIRK:
            # A falsified claim is included on purpose: "this looked true and
            # was not" is the warning an operator most needs before trying it.
            prefix = "known to be wrong: " if entry.body.get("falsified") else "watch out: "
            return ProposedStep(
                what=prefix + str(entry.body.get("claim") or entry.title)[:160],
                detail=str(entry.body.get("verdict") or ""),
                source=entry.source,
                evidence=entry.evidence,
            )
        case _:
            return None


def _fields(value: object) -> list[dict[str, object]]:
    return [field for field in value if isinstance(field, dict)] if isinstance(value, list) else []
