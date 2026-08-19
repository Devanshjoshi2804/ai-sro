"""A sentence to a decision: run this skill, choose between these, or neither.

Retrieval decides *what* is performed. The medium ladder decides *how*. Keeping
them apart is the point: escalating from network to UI to vision is a fallback
for a task we are sure about, and it must never stand in for being unsure which
task was asked for.
"""

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
"""Below this the reading is not used and the words are matched literally.

A model that says it is unsure is more useful than one that is confidently
wrong, and a deployment with no model at all falls here by construction --
which is worse, and is meant to be. Reading a sentence literally is an honest
kind of worse; pretending to understand it is not.
"""

_LIBRARY_PAGE = 200
"""Skills are ranked in memory. A tenant's library is dozens, not millions.

ponytail: when a library outgrows one page, this becomes a query -- the ranking
is already a pure function of (skills, utterance), so only the fetch moves.
"""


@dataclass(frozen=True, slots=True)
class Resolution:
    utterance: str
    verb: str = ""
    """What the reading said they want done. Carried so nothing downstream
    mistakes it for a value: "count the addresses" is not a question about a
    field called Count Type."""

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

    pursuit: Pursuit | None = None
    """What to do when nothing was taught: a goal composed from what is known,
    to be worked out on the screen. Never a dead end -- a person put in front of
    an unfamiliar screen does not refuse, and neither should this."""

    proposal: Proposal | None = None
    """When no skill matched: what the knowledge base says such a task would
    involve, with its sources. Never executed as though it were taught."""

    question: str | None = None
    """What to ask, when the honest answer is a question."""

    items: tuple[dict[str, str], ...] = ()
    """Parameter sets read out of the sentence. One per thing to do — "these
    six SKUs" is six. Shown as a table and confirmed before anything is sent,
    because getting this wrong is not a wrong answer, it is six wrong writes."""

    note: str = ""
    """What the extraction could not resolve."""

    why: tuple[str, ...] = field(default_factory=tuple)


class ResolveIntent:
    async def _read(self, utterance: str, after: str | None) -> Reading:
        """What the sentence means, or nothing when there is nobody to ask."""
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
    ) -> Resolution:
        async with self._uow as uow:
            skills = await uow.skills.list_for_tenant(ctx.tenant_id, limit=_LIBRARY_PAGE)

        if system:
            skills = tuple(s for s in skills if s.objective_key.target_system == system)

        # What the sentence means, read by something that reads sentences. The
        # phrase lists this replaces -- "how many", "which", "list all" -- were
        # each a guess about wording, and every one of them was broken by the
        # next thing somebody typed. "Show the list of all transport_mode then"
        # is a question by any reading and matched none of them.
        #
        # The reading decides nothing. It is matched against the skills that
        # exist and discarded where it names something that does not, so a
        # misreading costs a clarifying question rather than a wrong write.
        reading = await self._read(utterance, after)

        # A skill already under discussion, waiting for values it asked for.
        # Without this the answer to "what should the code be?" was resolved as
        # a fresh request, matched nothing, and the operator was asked the same
        # question again -- which is how a system teaches people not to answer
        # its questions.
        pending = next((s for s in skills if pinned and s.id.value == pinned), None)

        # What the sentence wants, read before anything is matched against it:
        # a question never matches a skill that writes, and which sentences are
        # questions is something a model reads better than a phrase list.
        asking = reading.wants == "ask" if reading.confidence >= _READ_FLOOR else asks(utterance)
        # The subject, where the reading was confident enough to name one. A
        # skill that explains the verb and not the subject answers about the
        # wrong thing, however well it scores.
        subject = reading.entity if reading.confidence >= _READ_FLOOR else ""
        candidates = rank(skills, utterance, question=asking, entity=subject)
        # A question is never an answer. "How many transport modes are there,
        # list them all" was swallowed by the create skill that was waiting for
        # a code and a description, because it named no other task confidently
        # -- so the operator asked for a list and was shown a form twice.
        #
        # Being asked something is the clearest possible signal that the last
        # question is no longer what is being talked about, and a pinned skill
        # that writes has no business answering one.
        # Asked something, or plainly about something else. Read rather than
        # pattern-matched: a pinned skill that writes has no business answering
        # a question, however the question happens to be phrased.
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
        # A follow-up carries none of its own nouns: "I want them in detail"
        # says nothing about transport modes, and resolving it alone sent the
        # operator back to the knowledge base for a subject they had just been
        # shown. The previous sentence supplies the subject; this one still has
        # to match something, so nothing is invented -- only remembered.
        if not candidates and after and (reading.continues or refers_back(utterance)):
            candidates = rank(skills, f"{after} {utterance}", question=asking, entity=subject)

        # A verb nothing does. "Delete all suppliers" shares its entity with
        # every supplier skill and scores well on all of them, so the reply was
        # "did you mean create or list?" -- offering two things that are not
        # what was asked, one of which writes. Nothing taught deletes anything,
        # and saying so is the only true answer.
        # Only for an instruction. A question is served by any read of the
        # entity -- "how many", "count", "show" and "list" are one another's
        # synonyms to everybody except a string comparison, and gating them on
        # the verb sent every question to the planner.
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

        if not candidates:
            return await self._nothing_taught(ctx, utterance, system)

        # Not while carrying on: the skill under discussion is not one of
        # several possibilities, it is the one that asked the question being
        # answered. Offering a choice here made the operator pick the same
        # skill again and lose what they had just typed.
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
        # A skill accounts for a sentence when it does what the sentence asked
        # for, not when it contains every word of it. "Show the list of all
        # transport modes" was read as list/transport mode with confidence, the
        # right skill was matched, and the reply still asked "did you mean?"
        # because "show" and "all" appear in no objective key -- hedging at the
        # operator about words the reading had already resolved.
        understood = reading.confidence >= _READ_FLOOR and (
            reading.verb.lower() in best.skill.objective_key.objective_type.lower()
            # A question answered by a read is understood, whatever verb they
            # used: "count the addresses" is served by the skill that lists
            # them, and hedging about the word "count" is hedging about a
            # synonym the reading already resolved.
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

        # Values second, and only for the skill that was chosen. Asking a model
        # which skill to run is the wrong-match failure with a model attached.
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
        """No skill was taught for this. Ask the knowledge base, not the ladder.

        The tempting mistake is to run the nearest skill in the browser and hope
        vision sorts it out. That is a confident wrong action; a proposal the
        operator can read is a slow correct one.
        """
        proposal = await self._planner.execute(ctx, utterance=utterance, system=system)
        # Not "teach me first". Everything known about the task is composed into
        # a goal, and the browser is driven toward it -- slowly, watched, and
        # captured, so the next time it is a taught skill over the API.
        pursuit = Pursuit.of(ctx, compose(utterance, proposal))
        pursuable = bool(pursuit.goal.facts)
        if asks(utterance):
            # A question that reached here did so because every skill that
            # matched it writes, and those were excluded rather than ranked.
            # Saying "teach me that task" to somebody who asked how many there
            # are would be answering a question with a form.
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
                # A pursuit with nothing known behind it is not a pursuit: there
                # is no screen to open and no field to fill, and pointing a model
                # at a blank browser is guessing with extra steps.
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
    """Whether this sentence is plainly about something else.

    Answering a question with a new request is allowed: an operator who asked
    for a transport mode and then said "actually, release the wave" means the
    second thing. What is not allowed is a pinned skill quietly swallowing it.
    """
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
    """Name plus what distinguishes it. Three skills called "Release Wave" are
    told apart by their facility, which is exactly why the key has one."""
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
