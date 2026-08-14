"""A sentence to a decision: run this skill, choose between these, or neither.

Retrieval decides *what* is performed. The medium ladder decides *how*. Keeping
them apart is the point: escalating from network to UI to vision is a fallback
for a task we are sure about, and it must never stand in for being unsure which
task was asked for.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sro.application.context import RequestContext
from sro.application.intent.match import Candidate, ambiguous, rank
from sro.application.intent.plan_task import PlanTask, Proposal
from sro.application.ports.repositories import UnitOfWork
from sro.domain.skill.parameter import ParameterKind
from sro.domain.skill.promotion import PromotionStage

_LIBRARY_PAGE = 200
"""Skills are ranked in memory. A tenant's library is dozens, not millions.

ponytail: when a library outgrows one page, this becomes a query -- the ranking
is already a pure function of (skills, utterance), so only the fetch moves.
"""


@dataclass(frozen=True, slots=True)
class Resolution:
    utterance: str

    matched: Candidate | None = None
    """The one skill this asks for, if exactly one does."""

    choices: tuple[Candidate, ...] = ()
    """Offered when two candidates are too close to separate. Choosing for the
    operator here is the wrong-match failure with extra steps."""

    missing_parameters: tuple[str, ...] = ()
    """Declared inputs with no value yet. A run cannot start without them, and
    asking is cheaper than a half-performed task."""

    runnable: bool = False
    """Whether the matched version may be performed at all. A `recorded` skill
    has not been reviewed by anybody."""

    confident: bool = False
    """False when the best skill cannot account for part of the sentence. The
    match is still offered -- it is probably right -- but as a question, because
    a partial match on a warehouse write is how the wrong thing gets done fast.
    """

    proposal: Proposal | None = None
    """When no skill matched: what the knowledge base says such a task would
    involve, with its sources. Never executed as though it were taught."""

    question: str | None = None
    """What to ask, when the honest answer is a question."""

    why: tuple[str, ...] = field(default_factory=tuple)


class ResolveIntent:
    def __init__(self, uow: UnitOfWork, planner: PlanTask) -> None:
        self._uow = uow
        self._planner = planner

    async def execute(
        self,
        ctx: RequestContext,
        *,
        utterance: str,
        system: str | None = None,
        parameters: dict[str, str] | None = None,
    ) -> Resolution:
        async with self._uow as uow:
            skills = await uow.skills.list_for_tenant(ctx.tenant_id, limit=_LIBRARY_PAGE)

        if system:
            skills = tuple(s for s in skills if s.objective_key.target_system == system)

        candidates = rank(skills, utterance)

        if not candidates:
            return await self._nothing_taught(ctx, utterance, system)

        if ambiguous(candidates):
            return Resolution(
                utterance=utterance,
                choices=candidates[:3],
                question=(
                    "More than one taught skill fits that. Which did you mean: "
                    + " or ".join(_describe(c) for c in candidates[:3])
                    + "?"
                ),
                why=candidates[0].why,
            )

        best = candidates[0]
        supplied = set(parameters or {})
        missing = tuple(
            sorted(
                parameter.name
                for parameter in best.version.parameters
                if parameter.kind is ParameterKind.INPUT and parameter.name not in supplied
            )
        )
        runnable = best.version.stage is not PromotionStage.RECORDED

        return Resolution(
            utterance=utterance,
            matched=best,
            choices=candidates[1:3],
            missing_parameters=missing,
            runnable=runnable,
            confident=best.confident,
            question=_question_for(best, missing, runnable),
            why=best.why,
        )

    async def _nothing_taught(
        self, ctx: RequestContext, utterance: str, system: str | None
    ) -> Resolution:
        """No skill was taught for this. Ask the knowledge base, not the ladder.

        The tempting mistake is to run the nearest skill in the browser and hope
        vision sorts it out. That is a confident wrong action; a proposal the
        operator can read is a slow correct one.
        """
        proposal = await self._planner.execute(ctx, utterance=utterance, system=system)
        return Resolution(
            utterance=utterance,
            proposal=proposal,
            question=(
                "Nothing has been taught for that. "
                + (
                    "Here is what the knowledge base says about it — review it, or teach me "
                    "the task and I will do it exactly as you do."
                    if proposal is not None and proposal.steps
                    else "Teach me the task once and I will have it."
                )
            ),
        )


def _describe(candidate: Candidate) -> str:
    """Name plus what distinguishes it. Three skills called "Release Wave" are
    told apart by their facility, which is exactly why the key has one."""
    key = candidate.skill.objective_key
    return f"{candidate.skill.name} ({key.target_system}/{key.facility})"


def _question_for(candidate: Candidate, missing: tuple[str, ...], runnable: bool) -> str | None:
    if not candidate.confident:
        return (
            f"Did you mean {_describe(candidate)}? "
            f"Nothing it does accounts for {', '.join(candidate.unexplained)}."
        )
    if not runnable:
        return (
            f"{candidate.skill.name} has not been reviewed yet. "
            "Promote it to shadow before it runs against the system."
        )
    if missing:
        return "I need " + ", ".join(missing) + "."
    return None
