from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sro.application.context import RequestContext
from sro.application.intent.match import (
    FLOOR,
    Candidate,
    ambiguous,
    asks,
    rank,
    refers_back,
    writes,
)
from sro.application.intent.plan_task import PlanTask, Proposal
from sro.application.intent.pursue import Pursuit, compose
from sro.application.ports.intent import IntentParser, Reading
from sro.application.ports.repositories import UnitOfWork
from sro.domain.skill.parameter import ParameterKind
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill

logger = logging.getLogger(__name__)

_READ_FLOOR = 0.5

_LIBRARY_PAGE = 200


@dataclass(frozen=True, slots=True)
class Resolution:
    utterance: str
    verb: str = ""

    matched: Candidate | None = None

    choices: tuple[Candidate, ...] = ()

    missing_parameters: tuple[str, ...] = ()

    runnable: bool = False

    confident: bool = False

    pursuit: Pursuit | None = None

    proposal: Proposal | None = None

    question: str | None = None

    items: tuple[dict[str, str], ...] = ()

    note: str = ""

    why: tuple[str, ...] = field(default_factory=tuple)

    about_what_stands: bool = False


class ResolveIntent:
    async def _read(self, utterance: str, after: str | None) -> Reading:
        if self._parser is None or not self._parser.available:
            return Reading()
        try:
            return await self._parser.read(utterance, after=after or "")
        except Exception:
            logger.warning("could not read the request; matching the words instead")
            return Reading()

    def __init__(
        self, uow: UnitOfWork, planner: PlanTask, parser: IntentParser | None = None
    ) -> None:
        self._uow = uow
        self._planner = planner
        self._parser = parser

    async def execute(
        self,
        ctx: RequestContext,
        *,
        utterance: str,
        system: str | None = None,
        parameters: dict[str, str] | None = None,
        after: str | None = None,
        pinned: str | None = None,
        standing: bool = False,
    ) -> Resolution:
        async with self._uow as uow:
            skills = await uow.skills.list_for_tenant(ctx.tenant_id, limit=_LIBRARY_PAGE)

        if system:
            skills = tuple(s for s in skills if s.objective_key.target_system == system)

        reading = await self._read(utterance, after)

        pending = next((s for s in skills if pinned and s.id.value == pinned), None)

        asking = reading.wants == "ask" if reading.confidence >= _READ_FLOOR else asks(utterance)
        subject = reading.entity if reading.confidence >= _READ_FLOOR else ""
        candidates = rank(skills, utterance, question=asking, entity=subject)
        interrupted = (
            pending is not None
            and writes(pending.runnable or pending.latest)
            and (asking or (reading.confidence >= _READ_FLOOR and not reading.continues))
        )
        carrying_on = (
            pending is not None and not interrupted and not _names_another(candidates, pending)
        )
        if pending is not None and carrying_on:
            candidates = (
                _pinned_candidate(pending),
                *(c for c in candidates if c.skill.id != pending.id),
            )
        if not candidates and after and (reading.continues or refers_back(utterance)):
            candidates = rank(skills, f"{after} {utterance}", question=asking, entity=subject)

        if (
            candidates
            and reading.wants == "act"
            and reading.confidence >= _READ_FLOOR
            and reading.verb
        ):
            wanted = reading.verb.lower()
            if not any(
                wanted in candidate.skill.objective_key.objective_type.lower()
                or candidate.skill.objective_key.objective_type.lower() in wanted
                for candidate in candidates
            ):
                candidates = ()

        if not candidates and standing:
            return Resolution(utterance=utterance, about_what_stands=True)
        if not candidates:
            return await self._nothing_taught(ctx, utterance, system)

        if ambiguous(candidates) and not carrying_on:
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
        understood = reading.confidence >= _READ_FLOOR and (
            reading.verb.lower() in best.skill.objective_key.objective_type.lower()
            or (asking and not writes(best.version))
        )
        supplied = set(parameters or {})
        missing = tuple(
            sorted(
                parameter.name
                for parameter in best.version.parameters
                if parameter.kind is ParameterKind.INPUT and parameter.name not in supplied
            )
        )
        runnable = best.version.stage is not PromotionStage.RECORDED

        items: tuple[dict[str, str], ...] = ()
        note = ""
        declared = tuple(p.name for p in best.version.parameters if p.kind is ParameterKind.INPUT)
        if self._parser is not None and self._parser.available and declared:
            extraction = await self._parser.extract(
                utterance, parameters=declared, context=best.version.summary
            )
            items = tuple({**(parameters or {}), **item} for item in extraction.items)
            note = extraction.note
            if items:
                missing = tuple(
                    sorted({name for item in items for name in declared if name not in item})
                )

        return Resolution(
            utterance=utterance,
            verb=reading.verb,
            matched=best,
            choices=candidates[1:3],
            missing_parameters=missing,
            runnable=runnable,
            confident=best.confident or understood,
            items=items,
            note=note,
            question=_question_for(best, missing, runnable, confident=best.confident or understood),
            why=best.why,
        )

    async def _nothing_taught(
        self, ctx: RequestContext, utterance: str, system: str | None
    ) -> Resolution:
        proposal = await self._planner.execute(ctx, utterance=utterance, system=system)
        pursuit = Pursuit.of(ctx, compose(utterance, proposal))
        pursuable = bool(pursuit.goal.facts)
        if asks(utterance):
            return Resolution(
                utterance=utterance,
                proposal=proposal,
                pursuit=pursuit if pursuable else None,
                question=(
                    "Nobody has demonstrated reading that, so I will work it out on the "
                    "screen and keep what I learn."
                    if pursuit.goal.facts
                    else "Nobody has demonstrated that and the knowledge base has nothing "
                    "on it. Show me once where you would look."
                ),
            )
        return Resolution(
            utterance=utterance,
            proposal=proposal,
            pursuit=pursuit if pursuable else None,
            question=(
                (pursuit.question if pursuit.goal.facts else None)
                or "Nothing has been taught for that. "
                + (
                    "Here is what the knowledge base says about it — review it, or teach me "
                    "the task and I will do it exactly as you do."
                    if proposal is not None and proposal.steps
                    else "Teach me the task once and I will have it."
                )
            ),
        )


def _names_another(candidates: tuple[Candidate, ...], pending: Skill) -> bool:
    best = candidates[0] if candidates else None
    return best is not None and best.skill.id != pending.id and best.confident


def _pinned_candidate(skill: Skill) -> Candidate:
    return Candidate(
        skill=skill,
        version=skill.runnable or skill.latest,
        score=FLOOR,
        why=("carried on from the question before it",),
    )


def _describe(candidate: Candidate) -> str:
    key = candidate.skill.objective_key
    return f"{candidate.skill.name} ({key.target_system}/{key.facility})"


def _question_for(
    candidate: Candidate, missing: tuple[str, ...], runnable: bool, *, confident: bool | None = None
) -> str | None:
    if not (candidate.confident if confident is None else confident):
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
