from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from urllib.parse import urlsplit

from sro.application.capture.identity import systems_touched
from sro.application.context import RequestContext
from sro.application.induction import assertions as assertion_extraction
from sro.application.induction import binding, describe, lookups, loops, narration
from sro.application.induction.companions import ambiguity_in, read_skills
from sro.application.induction.diff import (
    Alignment,
    Choice,
    OptionalFill,
    Parameterisation,
    Substitution,
    _longest_common,
    align,
    align_all,
    optional_fills,
    parameterise,
    typed_values,
)
from sro.application.induction.diff import (
    settled as without_corrections,
)
from sro.application.induction.emit import emit_step
from sro.application.induction.errors import InductionFailed
from sro.application.induction.frequency import Standing, standing_of
from sro.application.induction.lookups import PlannedLookup
from sro.application.induction.sites import ActionValueSite, JsonBodySite
from sro.application.induction.understand import as_evidence
from sro.application.knowledge.open_questions import Ambiguity, AskAbout
from sro.application.ports.interpretation import Reading, WorkflowInterpreter
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.recording import Recording, RecordingStatus
from sro.domain.shared.identifiers import RecordingId, SkillId
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.parameter import Parameter, ParameterKind
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
        others: Sequence[RecordingId] = (),
    ) -> InducedSkill:
        now = self._clock.now()

        async with self._uow as uow:
            run_a = await uow.recordings.get(ctx.tenant_id, first)
            run_b = run_a if second is None else await uow.recordings.get(ctx.tenant_id, second)
            objective = _check_pairable(run_a, run_b, paired=second is not None)

            rest = [
                await uow.recordings.get(ctx.tenant_id, other)
                for other in others
                if other not in (run_a.id, run_b.id)
            ]
            contributing = [
                other
                for other in rest
                if other.status is RecordingStatus.SEALED and other.objective_key == objective
            ]
            history = tuple(without_corrections(other.frames) for other in contributing)

            looped = loops.detect(run_a.frames, run_b.frames) if second is not None else None
            keep = looped.keep if looped is not None else None
            frames_a = without_corrections(run_a.frames[:keep])
            frames_b = without_corrections(run_b.frames[:keep])
            if looped is not None:
                looped = loops.in_step_space(looped, frames_a, frames_b)

            parameterisation = parameterise(frames_a, frames_b, others=history)

            pairs = align(frames_a, frames_b)
            planned = lookups.plan(
                _wanted(parameterisation),
                tuple(pair[0] for pair in pairs),
                tuple(pair[1] for pair in pairs),
                screens=frames_a,
                others=tuple(history),
                system=objective.target_system,
                facility=objective.facility,
            )
            resolvable = frozenset(found.field for found in planned)
            asked = await self._settle_choices(
                ctx,
                objective,
                tuple(c for c in parameterisation.choices if c.field not in resolvable),
            )
            if asked or resolvable:
                parameterisation = parameterise(
                    frames_a, frames_b, ask_for=asked | resolvable, others=history
                )
            if second is None:
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
                        others=history,
                    )
            if looped is not None:
                parameterisation = _with_loop(parameterisation, looped)

            doings = (frames_a, frames_b) if looped is not None else (frames_a, frames_b, *history)
            alignment = align_all(doings)
            conditionals = _extra_steps(
                alignment=alignment,
                pairs=pairs,
                runs=doings,
                parameterisation=parameterisation,
            )
            if conditionals and looped is not None:
                inside = [
                    conditional
                    for conditional in conditionals
                    if looped.loop.first_step < conditional.at <= looped.loop.last_step
                ]
                if inside:
                    raise InductionFailed(
                        "this pair is a loop whose body has a field somebody filled on "
                        "some iterations and not others. Whether that is one block with "
                        "an optional step in it or two different blocks is not something "
                        "the two runs decide. Demonstrate the loop with that field "
                        "filled every time round, or left out every time",
                        step_index=inside[0].frame.index,
                    )
            parameterisation = _make_room(parameterisation, conditionals)
            if looped is not None and conditionals:
                looped = replace(
                    looped,
                    loop=replace(
                        looped.loop,
                        over_step_index=_moved(looped.loop.over_step_index, conditionals),
                        first_step=_moved(looped.loop.first_step, conditionals),
                        last_step=_moved(looped.loop.last_step, conditionals),
                    ),
                )
            steps = _build_steps(
                frames_a,
                frames_b,
                run_a,
                objective,
                parameterisation,
                conditionals,
                _Counts(alignment, pairs, frames_a),
            )
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
            steps, described = await self._narrate(
                recording=run_a, steps=steps, described=described
            )
            version = SkillVersion(
                version=skill.next_version_number(),
                steps=steps,
                parameters=parameters,
                provenance=Provenance(
                    recording_ids=(
                        (run_a.id, run_b.id, *(other.id for other in rest))
                        if second is not None
                        else (run_a.id,)
                    ),
                    aligned_recording_ids=(
                        (
                            (run_a.id, run_b.id)
                            if looped is not None
                            else (run_a.id, run_b.id, *(other.id for other in contributing))
                        )
                        if second is not None
                        else (run_a.id,)
                    ),
                    induced_at=now,
                    induced_by=ctx.principal_id,
                    note=_provenance_note(run_a, run_b, paired=second is not None),
                ),
                summary=described.summary,
                when_to_use=described.when_to_use,
                systems=systems_touched(
                    await uow.connections.list_for_tenant(ctx.tenant_id), run_a, run_b
                ),
                starts_on=_started_on(run_a, run_b),
                loops=(looped.loop,) if looped is not None else (),
            )
            _refuse_an_unfillable_input(version)
            if (found := ambiguity_in(frames_a, objective)) is not None:
                await self._ask.raise_question(ctx, found)

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
                    known.latest.describe(summary=fresh.summary, when_to_use=fresh.when_to_use)
                await uow.skills.save(known)

            skill.add_version(version)
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


def _refuse_an_unfillable_input(version: SkillVersion) -> None:
    fillable = frozenset(
        name
        for step in version.steps
        if step.ui_plan is not None
        for name in step.ui_plan.placeholders
    )
    if any(
        parameter.kind is ParameterKind.INPUT
        and parameter.optional
        and parameter.options is None
        and parameter.name not in fillable
        for parameter in version.parameters
    ):
        raise InductionFailed(
            "this skill would ask for something no step of it can actually type or choose "
            "on the screen. Demonstrate that value being entered directly, not just picked "
            "another way, so there is a step that can fill it in"
        )


ASK_EACH_TIME = "ask each time"


def choice_key(objective: ObjectiveKey, field: str) -> str:
    return f"{objective.target_system}/{objective.entity_type}/{objective.objective_type}/{field}"


def _wanted(parameterisation: Parameterisation) -> tuple[lookups.Wanted, ...]:
    steps_of: dict[str, int] = {}
    for index, subs in sorted(parameterisation.substitutions.items()):
        for substitution in subs:
            steps_of.setdefault(substitution.parameter, index)
    return tuple(
        lookups.Wanted(field=choice.field, values=(choice.value,), step_index=choice.step_index)
        for choice in parameterisation.choices
    ) + tuple(
        lookups.Wanted(
            field=parameter.name,
            values=parameter.observed_values,
            step_index=steps_of[parameter.name],
        )
        for parameter in parameterisation.parameters
        if parameter.kind is ParameterKind.INPUT
        and parameter.options is None
        and parameter.observed_values
        and parameter.name in steps_of
    )


def with_options(
    parameters: tuple[Parameter, ...],
    planned: tuple[PlannedLookup, ...],
) -> tuple[Parameter, ...]:
    if not planned:
        return parameters
    options = {found.field: found for found in planned}
    return tuple(
        replace(
            parameter,
            options=options[parameter.name].options,
            description=(
                f"chosen from {_collection(options[parameter.name].options.url)}. "
                f"The demonstration used {options[parameter.name].shown}"
            ),
        )
        if parameter.name in options
        else parameter
        for parameter in parameters
    )


def _collection(url: str) -> str:
    path = urlsplit(url).path.rstrip("/")
    return path.rsplit("/", 1)[-1] or path


def _with_loop(parameterisation: Parameterisation, looped: loops.LoopFound) -> Parameterisation:
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


@dataclass(frozen=True, slots=True)
class _Conditional:
    frame: ActionFrame
    at: int

    parameter: str | None


def _conditionals(
    parameterisation: Parameterisation,
    fills: tuple[OptionalFill, ...],
    *,
    promised: bool = True,
) -> tuple[_Conditional, ...]:
    optional = {parameter.name for parameter in parameterisation.parameters if parameter.optional}
    named = {
        sub.site.pointer: sub.parameter
        for subs in parameterisation.substitutions.values()
        for sub in subs
        if isinstance(sub.site, JsonBodySite) and sub.parameter in optional
    }
    for fill in fills:
        if fill.pointer not in named and promised:
            raise InductionFailed(
                f"one run filled {fill.pointer} and the other left it alone, but nothing in "
                f"the diff calls that field optional; the runs are not two runs of one task",
                step_index=fill.frame.index,
            )
    return tuple(
        _Conditional(frame=fill.frame, at=fill.at, parameter=named[fill.pointer])
        for fill in fills
        if fill.pointer in named
    )


def _extra_steps(
    *,
    alignment: Alignment,
    pairs: tuple[tuple[ActionFrame, ActionFrame], ...],
    runs: tuple[tuple[ActionFrame, ...], ...],
    parameterisation: Parameterisation,
) -> tuple[_Conditional, ...]:
    frames_a = runs[0]
    spine = _reconcile(alignment, pairs, frames_a)
    before: dict[int, int] = {}
    running = 0
    for index in range(len(alignment.reference)):
        before[index] = running
        running += len(spine[index])

    excused = {id(fill.frame): fill for fill in optional_fills(frames_a, runs[1])}
    owner = {id(frame): run for run in runs for frame in run}

    promised: list[tuple[int, OptionalFill]] = []
    loose: list[tuple[int, OptionalFill]] = []
    plain: list[tuple[int, ActionFrame]] = []
    for index, frame in enumerate(alignment.reference):
        if spine[index]:
            continue
        fill = excused.get(id(frame))
        if fill is not None:
            promised.append((index, replace(fill, at=before[index])))
            continue
        run = owner[id(frame)]
        if run is frames_a or run is runs[1]:
            plain.append((index, frame))
            continue
        pointer = _key_typed_into(frame, run)
        if pointer is None:
            plain.append((index, frame))
            continue
        loose.append((index, OptionalFill(frame=frame, pointer=pointer, at=before[index])))

    conditionals = [
        *_conditionals(parameterisation, tuple(fill for _, fill in promised)),
        *_conditionals(parameterisation, tuple(fill for _, fill in loose), promised=False),
    ]
    gated = {
        index: conditional.parameter
        for index, fill in (*promised, *loose)
        for conditional in conditionals
        if conditional.frame is fill.frame and conditional.parameter is not None
    }

    standing = standing_of(alignment, _at_reference(parameterisation, spine, gated))
    for index, paired in spine.items():
        if paired and standing[index] is not Standing.ALWAYS:
            logger.info(
                "keeping step %s: both demonstrations made it, though only %d of the doings did",
                ", ".join(str(step) for step in paired),
                alignment.seen[index],
            )
    for index, frame in plain:
        if standing[index] is not Standing.ALWAYS:
            logger.info(
                "dropping a step %d of the doings made and nothing accounts for: %s",
                alignment.seen[index],
                frame.action.kind,
            )
            continue
        if frame.action.value or frame.action.secret or frame.primary_request is not None:
            raise InductionFailed(
                f"{alignment.seen[index]} of the doings made a step neither demonstration "
                f"did, and it carries a value nothing diffed: {frame.action.kind}. "
                "Demonstrate the task twice with that step in it",
                step_index=frame.index,
            )
        conditionals.append(_Conditional(frame=frame, at=before[index], parameter=None))

    return tuple(
        sorted(conditionals, key=lambda conditional: (conditional.at, conditional.frame.index))
    )


def _key_typed_into(frame: ActionFrame, run: tuple[ActionFrame, ...]) -> str | None:
    return next(
        (pointer for write in run if (pointer := binding.key_filled_by(frame, write)) is not None),
        None,
    )


class _Counts:
    def __init__(
        self,
        alignment: Alignment,
        pairs: tuple[tuple[ActionFrame, ActionFrame], ...],
        frames_a: tuple[ActionFrame, ...],
    ) -> None:
        self.doings = alignment.doings
        self._paired = {
            index: alignment.seen[reference]
            for reference, paired in _reconcile(alignment, pairs, frames_a).items()
            for index in paired
        }
        self._by_frame = {
            id(frame): alignment.seen[index] for index, frame in enumerate(alignment.reference)
        }

    def paired(self, index: int) -> int:
        return self._paired.get(index, 0)

    def frame(self, frame: ActionFrame) -> int:
        return self._by_frame.get(id(frame), 0)


def _reconcile(
    alignment: Alignment,
    pairs: tuple[tuple[ActionFrame, ActionFrame], ...],
    frames_a: tuple[ActionFrame, ...],
) -> dict[int, tuple[int, ...]]:
    counterpart = {
        id(reference): frame for reference, frame in _longest_common(alignment.reference, frames_a)
    }
    exploded: dict[int, list[int]] = {}
    for index, (frame_a, _) in enumerate(pairs):
        exploded.setdefault(frame_a.index, []).append(index)
    return {
        index: tuple(exploded.get(counterpart[id(frame)].index, ()))
        if id(frame) in counterpart
        else ()
        for index, frame in enumerate(alignment.reference)
    }


def _at_reference(
    parameterisation: Parameterisation,
    spine: dict[int, tuple[int, ...]],
    gated: dict[int, str],
) -> Parameterisation:
    optional = {parameter.name for parameter in parameterisation.parameters if parameter.optional}
    at: dict[int, list[Substitution]] = {}
    for index, paired in spine.items():
        for step in paired:
            at.setdefault(index, []).extend(parameterisation.substitutions.get(step, ()))
    for index, parameter in gated.items():
        at.setdefault(index, []).append(Substitution(site=ActionValueSite(), parameter=parameter))

    for subs in at.values():
        two_valued = {
            sub.parameter
            for sub in subs
            if isinstance(sub.site, ActionValueSite) and sub.parameter in optional
        }
        if len(two_valued) > 1:
            raise InductionFailed(
                f"one gesture types {' and '.join(sorted(two_valued))}, and both are fields "
                "some doing left empty. A step that happens only when two supplied values are "
                "both present cannot be written down; demonstrate them as separate gestures"
            )
    return replace(parameterisation, substitutions={k: tuple(v) for k, v in at.items()})


def _moved(index: int, conditionals: tuple[_Conditional, ...]) -> int:
    return index + sum(1 for conditional in conditionals if conditional.at <= index)


def _make_room(
    parameterisation: Parameterisation, conditionals: tuple[_Conditional, ...]
) -> Parameterisation:
    if not conditionals:
        return parameterisation
    substitutions = {
        _moved(index, conditionals): subs for index, subs in parameterisation.substitutions.items()
    }
    for position, conditional in enumerate(conditionals):
        if conditional.parameter is None:
            continue
        substitutions[conditional.at + position] = (
            Substitution(site=ActionValueSite(), parameter=conditional.parameter),
        )
    return replace(
        parameterisation,
        parameters=tuple(
            parameter
            if parameter.source_step_index is None
            else replace(
                parameter,
                source_step_index=_moved(parameter.source_step_index, conditionals),
            )
            for parameter in parameterisation.parameters
        ),
        substitutions=substitutions,
    )


def _stamped(step: SkillStep, seen_in: int, of_doings: int) -> SkillStep:
    return replace(step, seen_in=seen_in, of_doings=of_doings if seen_in else 0)


def _build_steps(
    run_a_frames: tuple[ActionFrame, ...],
    run_b_frames: tuple[ActionFrame, ...],
    run_a: Recording,
    objective: ObjectiveKey,
    parameterisation: Parameterisation,
    conditionals: tuple[_Conditional, ...] = (),
    counts: _Counts | None = None,
) -> tuple[SkillStep, ...]:
    pairs = align(run_a_frames, run_b_frames)
    frames_a = [pair[0] for pair in pairs]
    frames_b = [pair[1] for pair in pairs]
    said = narration.align(tuple(frames_a), run_a.narration)

    steps: list[SkillStep] = []
    pending = list(conditionals)
    for index in range(len(frames_a) + 1):
        while pending and pending[0].at <= index:
            branch = pending.pop(0)
            steps.append(
                _stamped(
                    _emit_conditional(len(steps), branch, parameterisation, objective),
                    counts.frame(branch.frame) if counts else 0,
                    counts.doings if counts else 0,
                )
            )
        if index == len(frames_a):
            break
        steps.append(
            _stamped(
                emit_step(
                    len(steps),
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
                ),
                counts.paired(index) if counts else 0,
                counts.doings if counts else 0,
            )
        )
    return tuple(steps)


def _emit_conditional(
    index: int,
    conditional: _Conditional,
    parameterisation: Parameterisation,
    objective: ObjectiveKey,
) -> SkillStep:
    logger.info(
        "step %d is a gesture with nothing to check: %s%s",
        index,
        conditional.frame.action.kind,
        f", when {conditional.parameter}" if conditional.parameter else "",
    )
    return emit_step(
        index,
        replace(conditional.frame, requests=()),
        parameterisation,
        assertion_extraction.StepEvidence(assertions=(), wait_for=None),
        objective,
        when=conditional.parameter,
    )


async def _read_evidence(interpreter: WorkflowInterpreter | None, recording: Recording) -> Reading:
    if interpreter is None or not interpreter.available:
        return Reading()
    try:
        return await interpreter.read(as_evidence(recording))
    except Exception:
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


def _started_on(*recordings: Recording | None) -> str | None:
    began = {
        recording.frames[0].page_url
        for recording in recordings
        if recording is not None and recording.frames and recording.frames[0].page_url
    }
    return began.pop() if len(began) == 1 else None
