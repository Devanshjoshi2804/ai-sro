"""Turn two sealed recordings into a skill version."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from urllib.parse import urlsplit

from sro.application.capture.identity import systems_touched
from sro.application.context import RequestContext
from sro.application.induction import assertions as assertion_extraction
from sro.application.induction import describe, lookups, loops, narration
from sro.application.induction.companions import ambiguity_in, read_skills
from sro.application.induction.diff import (
    Choice,
    Parameterisation,
    Substitution,
    align,
    parameterise,
    typed_values,
)
from sro.application.induction.emit import emit_step
from sro.application.induction.errors import InductionFailed
from sro.application.induction.lookups import PlannedLookup
from sro.application.induction.understand import as_evidence
from sro.application.knowledge.open_questions import Ambiguity, AskAbout
from sro.application.ports.interpretation import Reading, WorkflowInterpreter
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.recording import Recording, RecordingStatus
from sro.domain.shared.identifiers import RecordingId, SkillId
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.parameter import Evidence, Parameter
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Provenance, Skill, SkillStep, SkillVersion
from sro.domain.skill.track_record import TrackRecord, Verdict

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class InducedSkill:
    skill_id: SkillId
    version: int
    step_count: int
    input_parameter_count: int
    derived_parameter_count: int


class InduceSkill:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        ids: IdFactory,
        ask: AskAbout,
        interpreter: WorkflowInterpreter | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids
        self._ask = ask
        self._interpreter = interpreter

    async def _narrate(
        self,
        *,
        recording: Recording,
        steps: tuple[SkillStep, ...],
        described: describe.Description,
    ) -> tuple[tuple[SkillStep, ...], describe.Description]:
        """Put what a model read over what the evidence decided.

        Words only. A step keeps its call, its locators and its assertions; what
        changes is the sentence above them, and a skill described as "click
        span#button-1337-btnIconEl" is one nobody can review or search for.
        """
        reading = await _read_evidence(self._interpreter, recording)
        if not reading.summary and not reading.steps:
            return steps, described

        said = {step.index: step for step in reading.steps}
        narrated = tuple(
            replace(step, intent=said[step.index].what.strip() or step.intent)
            if step.index in said and said[step.index].what.strip()
            else step
            for step in steps
        )
        return narrated, replace(
            described,
            summary=reading.summary.strip() or described.summary,
            when_to_use=reading.when_to_use.strip() or described.when_to_use,
        )

    async def _settle_choices(
        self,
        ctx: RequestContext,
        objective: ObjectiveKey,
        choices: tuple[Choice, ...],
    ) -> frozenset[str]:
        """Ask about each chosen constant once, and apply what was answered.

        Both demonstrations sent one address. That is either how this task is
        always done, or what that operator happened to pick twice, and nothing
        in these two recordings can tell those apart. Guessing either way is the
        failure this system is arranged against: replay the constant and every
        supplier lands on one address; parameterise it and the operator is
        interrogated about a field they never think about.

        So the question is written down, the skill is induced exactly as it was
        demonstrated in the meantime, and an answer changes the next induction.
        """
        wanted: set[str] = set()
        for choice in choices:
            key = choice_key(objective, choice.field)
            answer = await self._ask.settled(ctx, key=key)
            if answer == ASK_EACH_TIME:
                wanted.add(choice.field)
                continue
            if answer is not None:
                continue
            await self._ask.raise_question(
                ctx,
                Ambiguity(
                    system=objective.target_system,
                    key=key,
                    question=(
                        f"Both demonstrations used {choice.value!r} for {choice.field}. "
                        "Is that always the value, or should whoever runs it choose?"
                    ),
                    options=(choice.value, ASK_EACH_TIME),
                    because=(
                        f"step {choice.step_index} sends it",
                        f"step {choice.seen_at} listed it, so it was chosen from the screen",
                    ),
                ),
            )
        return frozenset(wanted)

    async def execute(
        self,
        ctx: RequestContext,
        *,
        first: RecordingId,
        second: RecordingId | None = None,
        name: str | None = None,
    ) -> InducedSkill:
        """Two demonstrations, or one.

        Two is the design: what differs between them is a parameter, what holds
        is literal, and nothing is inferred. One is a deliberate second choice --
        the operator says "this is the whole task, exactly as I did it" -- and it
        is honest about what that costs. A single run is diffed against itself,
        so every value it sent stays exactly as demonstrated and the skill has no
        parameters at all. It replays one specific act; teaching it a second time
        is what turns the values in it into questions.
        """
        now = self._clock.now()

        async with self._uow as uow:
            run_a = await uow.recordings.get(ctx.tenant_id, first)
            run_b = run_a if second is None else await uow.recordings.get(ctx.tenant_id, second)
            objective = _check_pairable(run_a, run_b, paired=second is not None)

            # Two demonstrations that did the same block a different number of
            # times are two lengths of one looping task, not two tasks. Read
            # first, because everything below works on the frames that survive:
            # the prefix and one iteration, which is what the skill keeps.
            looped = loops.detect(run_a.frames, run_b.frames) if second is not None else None
            keep = looped.keep if looped is not None else None
            frames_a, frames_b = run_a.frames[:keep], run_b.frames[:keep]

            parameterisation = parameterise(frames_a, frames_b)

            # An id the operator picked off a screen is not something to ask a
            # human for -- they picked it by reading a name, and the screen that
            # showed them both is in the recording. Where that can be read, the
            # skill carries the lookup; where it cannot, the id is a question.
            pairs = align(frames_a, frames_b)
            planned = lookups.plan(
                parameterisation.choices,
                tuple(pair[0] for pair in pairs),
                tuple(pair[1] for pair in pairs),
                {parameter.name for parameter in parameterisation.parameters},
                screens=frames_a,
                system=objective.target_system,
                facility=objective.facility,
            )
            resolvable = frozenset(found.choice.field for found in planned)
            asked = await self._settle_choices(
                ctx,
                objective,
                tuple(c for c in parameterisation.choices if c.field not in resolvable),
            )
            if asked or resolvable:
                parameterisation = parameterise(frames_a, frames_b, ask_for=asked | resolvable)
            if second is None:
                # One demonstration cannot disagree with itself, so nothing it
                # sent looked like a parameter -- including the values a person
                # typed. Those are asked for: a box the operator filled in is
                # the clearest evidence in the whole recording that the next run
                # wants a different answer.
                typed = typed_values(
                    frames_a,
                    {parameter.name for parameter in parameterisation.parameters},
                )
                if typed:
                    parameterisation = parameterise(
                        frames_a,
                        frames_b,
                        ask_for=frozenset(asked | resolvable | {c.field for c in typed}),
                        also=typed,
                    )
            if looped is not None:
                parameterisation = _with_loop(parameterisation, looped)
            steps = _build_steps(frames_a, frames_b, run_a, objective, parameterisation)
            parameters = with_options(parameterisation.parameters, planned)

            skill = await uow.skills.find_by_objective(ctx.tenant_id, objective)
            if skill is None:
                skill = Skill(
                    id=self._ids.new_skill_id(),
                    tenant_id=ctx.tenant_id,
                    objective_key=objective,
                    name=name or objective.objective_type.replace("_", " ").title(),
                    created_at=now,
                )
                await uow.skills.add(skill)

            described = describe.compose(objective, steps, parameters)
            # What it was for, in the warehouse's own words, where a model can
            # read it. Only the words: the steps, the parameters and the calls
            # are already decided, and a reading that disagreed with them would
            # be describing a skill nobody induced.
            #
            # Both halves earn their place. Asked to say what a demonstration
            # was, the model answered "creates a new supplier by entering a
            # supplier number, looking up an address and assigning a client" --
            # which is the task. Asked which values vary, it named the client
            # and missed the supplier number that was typed in front of it.
            steps, described = await self._narrate(
                recording=run_a, steps=steps, described=described
            )
            version = SkillVersion(
                version=skill.next_version_number(),
                steps=steps,
                parameters=parameters,
                provenance=Provenance(
                    recording_ids=(run_a.id, run_b.id) if second is not None else (run_a.id,),
                    induced_at=now,
                    induced_by=ctx.principal_id,
                    note=_provenance_note(run_a, run_b, paired=second is not None),
                ),
                summary=described.summary,
                when_to_use=described.when_to_use,
                systems=systems_touched(
                    await uow.connections.list_for_tenant(ctx.tenant_id), run_a, run_b
                ),
                loops=(looped.loop,) if looped is not None else (),
            )
            # Everything else the demonstration proved. Opening the screen to
            # create a transport mode lists the existing ones first, and that
            # read is real evidence -- asking the operator to demonstrate it
            # separately is asking them for something already in hand.
            # Where two readings of one entity were both observed, the system
            # says so rather than choosing. Asked once, answered once, and read
            # by everything afterwards.
            if (found := ambiguity_in(frames_a, objective)) is not None:
                await self._ask.raise_question(ctx, found)

            # What somebody already said their words mean, if they have said.
            settled = await self._ask.settled(
                ctx, key=f"{objective.target_system}/{objective.entity_type}/collection"
            )
            for companion in read_skills(
                run_a.frames,
                prefer=settled,
                taught=objective,
                recording_id=run_a.id,
                tenant_id=ctx.tenant_id,
                by=ctx.principal_id,
                at=now,
                new_id=self._ids.new_skill_id,
            ):
                known = await uow.skills.find_by_objective(ctx.tenant_id, companion.objective_key)
                if known is None:
                    await uow.skills.add(companion)
                    continue
                # Known, but not necessarily right. The first supplier
                # demonstration built this read from a filter-column endpoint
                # and answered "how many suppliers" with five column
                # definitions; re-teaching the task changed nothing, because a
                # companion was only ever created and never corrected. A later
                # demonstration that reads a different call is later evidence.
                fresh = companion.latest
                if fresh.steps != known.latest.steps:
                    known.add_version(
                        replace(
                            fresh,
                            version=known.next_version_number(),
                            stage=PromotionStage.RECORDED,
                            track_record=TrackRecord(),
                        )
                    )
                    known.latest.earn(Verdict.WITHHELD, now)
                elif (fresh.summary, fresh.when_to_use) != (
                    known.latest.summary,
                    known.latest.when_to_use,
                ):
                    # Same calls, better words. A description is not a change to
                    # what runs, so it does not earn a version -- but leaving it
                    # stale left a skill announcing "there were 50" long after
                    # the system learned there were 234, and that sentence is
                    # what an operator's question is matched against.
                    known.latest.describe(summary=fresh.summary, when_to_use=fresh.when_to_use)
                await uow.skills.save(known)

            skill.add_version(version)
            # Straight to rehearsing, once it is attached: a version is added at
            # RECORDED and cannot be run there, so it could never earn the rung
            # that lets it run. Nothing is sent at the next one -- the request is
            # built and withheld for somebody to read, and withholding it from
            # the operator too is not caution, just a skill nobody can review.
            version.earn(Verdict.WITHHELD, now)
            await uow.skills.save(skill)
            await uow.commit()

        return InducedSkill(
            skill_id=skill.id,
            version=version.version,
            step_count=len(version.steps),
            input_parameter_count=len(version.inputs),
            derived_parameter_count=len(version.parameters) - len(version.inputs),
        )


def _check_pairable(run_a: Recording, run_b: Recording, *, paired: bool = True) -> ObjectiveKey:
    """The objective both demonstrations share, or why they do not share one."""
    if paired and run_a.id == run_b.id:
        raise InductionFailed(
            "a skill needs two different recordings; diffing one against itself would "
            "hardcode every value in it"
        )
    for recording in (run_a, run_b):
        if recording.status is not RecordingStatus.SEALED:
            raise InductionFailed(
                f"recording {recording.id} is {recording.status}; only sealed recordings "
                "can be induced"
            )
    key_a, key_b = run_a.objective_key, run_b.objective_key
    if key_a is None or key_b is None:  # pragma: no cover - sealing sets it
        raise InductionFailed("a sealed recording always names its objective; this one does not")
    if key_a != key_b:
        differing = ", ".join(
            field
            for field in ("objective_type", "target_system", "entity_type", "facility", "direction")
            if getattr(key_a, field) != getattr(key_b, field)
        )
        raise InductionFailed(
            f"these two demonstrations did different things: they disagree on {differing} "
            f"({key_a.slug()} and {key_b.slug()})"
        )
    return key_a


ASK_EACH_TIME = "ask each time"
"""The answer that turns a demonstrated constant into something the operator is
prompted for. The other answer is the value itself, which changes nothing."""


def choice_key(objective: ObjectiveKey, field: str) -> str:
    """Addressed by task and field, so re-teaching finds the answer rather than
    asking again."""
    return f"{objective.target_system}/{objective.entity_type}/{objective.objective_type}/{field}"


def with_options(
    parameters: tuple[Parameter, ...],
    planned: tuple[PlannedLookup, ...],
) -> tuple[Parameter, ...]:
    """Give each chosen id the list it was chosen from.

    The value stays what the call needs -- the id -- and stops being something
    a person has to know: the console draws a dropdown, fills it from the same
    endpoint the screen used, and what the operator picks is what runs.
    """
    if not planned:
        return parameters
    options = {found.choice.field: found for found in planned}
    return tuple(
        replace(
            parameter,
            options=options[parameter.name].options,
            description=(
                f"chosen from {_collection(options[parameter.name].options.url)}. "
                f"The demonstration used {options[parameter.name].shown}"
            ),
            evidence=Evidence.PROPOSED,
        )
        if parameter.name in options
        else parameter
        for parameter in parameters
    )


def _collection(url: str) -> str:
    path = urlsplit(url).path.rstrip("/")
    return path.rsplit("/", 1)[-1] or path


def _with_loop(parameterisation: Parameterisation, looped: loops.LoopFound) -> Parameterisation:
    """The loop's parameters and substitutions, and the diff's where they differ.

    Where both explain one site, the loop wins and the diff's reading of it goes
    away entirely. They are reading the same fact: the first iteration of run A
    adjusted line 1 and run B's adjusted line 7, so the ordinary diff sees a
    value that varies and calls it a question for an operator -- which is
    exactly the question the loop answers out of the list. Two parameters for
    one value would be a skill that asks for something it already knows, under
    a name that collides with the thing that knows it.
    """
    bound = {(index, sub.site) for index, subs in looped.substitutions.items() for sub in subs}
    kept: dict[int, tuple[Substitution, ...]] = {}
    for index, subs in parameterisation.substitutions.items():
        surviving = tuple(sub for sub in subs if (index, sub.site) not in bound)
        if surviving:
            kept[index] = surviving

    still_named = {sub.parameter for subs in kept.values() for sub in subs}
    parameters = tuple(
        parameter
        for parameter in parameterisation.parameters
        # A parameter the loop took over every site of has nothing left to
        # substitute. Choices the operator was asked about keep their place:
        # they have no sites yet and are not this pass's to drop.
        if parameter.name in still_named
        or not any(
            parameter.name == sub.parameter
            for subs in parameterisation.substitutions.values()
            for sub in subs
        )
    )

    for index, subs in looped.substitutions.items():
        kept[index] = (*kept.get(index, ()), *subs)
    return replace(
        parameterisation,
        parameters=(*parameters, *looped.parameters),
        substitutions=kept,
    )


def _build_steps(
    run_a_frames: tuple[ActionFrame, ...],
    run_b_frames: tuple[ActionFrame, ...],
    run_a: Recording,
    objective: ObjectiveKey,
    parameterisation: Parameterisation,
) -> tuple[SkillStep, ...]:
    """Frames rather than recordings, because a looping task keeps one iteration
    of its body: the recording holds all of them, and the skill is the block."""
    # The steps both runs share, in order. What only one operator did -- a field
    # clicked twice, a panel opened to check something -- is not part of the
    # task, and emitting it would make every replay repeat somebody's hesitation.
    pairs = align(run_a_frames, run_b_frames)
    frames_a = [pair[0] for pair in pairs]
    frames_b = [pair[1] for pair in pairs]
    # Run A's narration, because run A's frames are the ones being emitted. Run
    # B is here to disagree with A, not to describe it.
    said = narration.align(tuple(frames_a), run_a.narration)
    return tuple(
        emit_step(
            index,
            frames_a[index],
            parameterisation,
            assertion_extraction.extract(
                frames_a[index],
                frames_b[index],
                next_a=frames_a[index + 1] if index + 1 < len(frames_a) else None,
                next_b=frames_b[index + 1] if index + 1 < len(frames_b) else None,
            ),
            objective,
            frames_b[index],
            said.get(frames_a[index].index),
        )
        for index in range(len(frames_a))
    )


async def _read_evidence(interpreter: WorkflowInterpreter | None, recording: Recording) -> Reading:
    """The model's account of one demonstration, or an empty one."""
    if interpreter is None or not interpreter.available:
        return Reading()
    try:
        return await interpreter.read(as_evidence(recording))
    except Exception:
        # A description is worth having and never worth failing an induction
        # for: the skill is defined by the diff, and this only names it.
        logger.warning("could not read the demonstration for a description", exc_info=True)
        return Reading()


def _provenance_note(run_a: Recording, run_b: Recording, *, paired: bool = True) -> str:
    runs = (run_a, run_b) if paired else (run_a,)
    narrated = [r.id for r in runs if r.has_narration]
    alone = (
        ""
        if paired
        else "induced from one demonstration, so every value it sends is fixed as demonstrated"
    )
    if not narrated:
        return alone or "induced from two silent demonstrations"
    said = f"narration available on {', '.join(str(rid) for rid in narrated)}"
    return f"{alone}; {said}" if alone else said
