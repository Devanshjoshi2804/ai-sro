"""Turn two sealed recordings into a skill version."""

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
    # Named apart from the module's own `settled` local, which is an answer to
    # a question a person settled -- two unrelated meanings of one word, and
    # the shadowing kind of bug is one this session has already paid for.
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
        others: Sequence[RecordingId] = (),
    ) -> InducedSkill:
        """Two demonstrations, or one.

        Two is the design: what differs between them is a parameter, what holds
        is literal, and nothing is inferred. One is a deliberate second choice --
        the operator says "this is the whole task, exactly as I did it" -- and it
        is honest about what that costs. A single run is diffed against itself,
        so every value it sent stays exactly as demonstrated and the skill has no
        parameters at all. It replays one specific act; teaching it a second time
        is what turns the values in it into questions.

        ``others`` are the rest of the doings of this task, and they are read
        twice. Once by :func:`parameterise`, for whether some doing left a
        field empty -- an operator who created the same work area three times
        and left Absolute Priority empty the first time has proved the
        warehouse takes it empty, and a pair drawn from the two most recent
        doings never sees that. And once by :func:`align_all`, for the steps
        they made, which is what this used to throw away: four carrier cross
        references went in as one pair and two histories, the pair proved four
        parameters, and the address lookup left with the run that made it. The
        skill named ``cod_address_id`` and had no step that could type it.

        The pair still proves every parameter and still settles identity --
        ADR 004 is untouched. What the whole history now decides is which
        *steps* are the task: how often a step happened, and whether a rare one
        types a field somebody supplied. See ADR 015.
        """
        now = self._clock.now()

        async with self._uow as uow:
            run_a = await uow.recordings.get(ctx.tenant_id, first)
            run_b = run_a if second is None else await uow.recordings.get(ctx.tenant_id, second)
            objective = _check_pairable(run_a, run_b, paired=second is not None)

            # Read rather than checked. A doing that is not sealed, or that
            # named a different objective, is simply not evidence about this
            # task -- and refusing the whole induction over one would cost a
            # demonstration for a recording nothing was going to be built from.
            rest = [
                await uow.recordings.get(ctx.tenant_id, other)
                for other in others
                if other not in (run_a.id, run_b.id)
            ]
            # Named apart from `history` because `recording_ids` below cites
            # all of `rest` -- everything read, on the theory that a reader
            # asking "why is this recording in provenance" deserves the
            # answer even where the answer is "it named a different task and
            # nothing was built from it" -- while `aligned_recording_ids`
            # must cite only the ones that actually reached `align_all`,
            # which is this filtered subset and no other.
            contributing = [
                other
                for other in rest
                if other.status is RecordingStatus.SEALED and other.objective_key == objective
            ]
            history = tuple(without_corrections(other.frames) for other in contributing)

            # Two demonstrations that did the same block a different number of
            # times are two lengths of one looping task, not two tasks. Read
            # first, because everything below works on the frames that survive:
            # the prefix and one iteration, which is what the skill keeps.
            looped = loops.detect(run_a.frames, run_b.frames) if second is not None else None
            keep = looped.keep if looped is not None else None
            # Settled here, at the one seam where the runs enter induction, so
            # everything below -- the parameterisation, the alignment, the
            # conditional fills -- reads the same frames. A field typed twice
            # before anything was sent is one field filled once, and reading it
            # as two steps refused every pair of four doings of a real task.
            frames_a = without_corrections(run_a.frames[:keep])
            frames_b = without_corrections(run_b.frames[:keep])
            if looped is not None:
                # Detection reads raw frames and everything below counts the
                # steps the two runs share. Converted here, at the one seam
                # between them, rather than left for each reader to reconcile.
                looped = loops.in_step_space(looped, frames_a, frames_b)

            parameterisation = parameterise(frames_a, frames_b, others=history)

            # An id the operator picked off a screen is not something to ask a
            # human for -- they picked it by reading a name, and the screen that
            # showed them both is in the recording. Where that can be read, the
            # skill carries the lookup; where it cannot, the id is a question.
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
                        others=history,
                    )
            if looped is not None:
                parameterisation = _with_loop(parameterisation, looped)

            # The steps the pair alone does not have. Two sources, one rule.
            #
            # The gestures `align` dropped: one operator filled a field the
            # other left alone, and that keystroke is the only evidence in
            # either recording of how the field gets filled at all. And the
            # gestures of every other doing, which used to reach nothing -- the
            # address lookup among them. Both come back as steps, and how often
            # each happened decides whether it is one.
            #
            # And the pair alone where this is a loop, which is a real loss
            # taken deliberately. `keep` is a fact about *this pair* -- the
            # prefix and one iteration, found by `loops.detect` from two runs
            # being two lengths of one block -- and `history` is whole
            # recordings, however many times round each of them went. Handed
            # in untruncated, every doing's second and third iterations are
            # evidential frames the reference has no place for, so they are
            # spliced in at the end and they *agree with each other*: four
            # doings that looped twice make one extra body frame look like a
            # step four doings made. Past two thirds it is emitted -- as a
            # refusal where it carries the block's write, or as a duplicate
            # gesture sitting outside the loop where it does not.
            #
            # Excluded rather than truncated, and the difference is the
            # question each answers. Truncating asks "where does this doing's
            # own block stop", and nothing can answer it: `loops.detect` reads
            # two runs of differing length against each other and there is no
            # such thing for one run on its own, so any prefix taken here
            # would be the pair's `keep` applied to a recording that never
            # agreed to it. Excluding asks "how many doings made this step",
            # notices that a doing which made it five times cannot answer, and
            # declines to count it. A looping task therefore induces from its
            # pair exactly as it did before this change.
            #
            # ponytail: per-run loop detection would let a looping task read
            # its whole history too -- one block per doing, counted once.
            # Worth building when a looping task with more than two
            # demonstrations turns up; the pair still induces it today.
            doings = (frames_a, frames_b) if looped is not None else (frames_a, frames_b, *history)
            conditionals = _extra_steps(
                alignment=align_all(doings),
                pairs=pairs,
                runs=doings,
                parameterisation=parameterisation,
            )
            if conditionals and looped is not None:
                inside = [
                    conditional
                    for conditional in conditionals
                    # Strictly inside. A conditional at `first_step` is
                    # inserted immediately *before* the body and moves the
                    # whole block along; one past `last_step` lands after it.
                    # Only a gesture between the two is part of an iteration.
                    if looped.loop.first_step < conditional.at <= looped.loop.last_step
                ]
                if inside:
                    # A field filled on some times round and not others. Both
                    # readings are available and the evidence does not choose:
                    # the block is one iteration with a conditional step in it,
                    # or it is two different iterations and not a loop at all.
                    # A conditional *before* the body is no longer a problem --
                    # both indices move together now -- so only this is left.
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
                # The conditional steps take their places among the aligned
                # ones and everything after them moves along. The loop's body
                # counts the same steps, so it moves by the same rule -- which
                # is what `_moved` was always for.
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
                frames_a, frames_b, run_a, objective, parameterisation, conditionals
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
                    # Every doing the induction read, including those read
                    # only for what somebody left empty: a reviewer asked why a
                    # field is optional has to be able to go and look at the
                    # doing that proves it.
                    recording_ids=(
                        (run_a.id, run_b.id, *(other.id for other in rest))
                        if second is not None
                        else (run_a.id,)
                    ),
                    # The same shape `doings` was built in, above, translated
                    # from frames to the ids that own them -- not recomputed
                    # by some other rule that could quietly drift from it.
                    # `contributing` is `rest` filtered to what `history`
                    # actually held, so a recording that named a different
                    # objective or was never sealed is honestly absent from
                    # both, not counted as aligned on the strength of merely
                    # having been passed in.
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
                # Already moved, above, and carried here as it stands. The
                # loop's bounds count aligned steps like every other index
                # induction produces -- `loops.in_step_space` converts them
                # once, immediately after detection -- so a conditional step
                # taking its place among the aligned ones moves them by the
                # same rule as the substitutions, which is what `_moved` is
                # for.
                #
                # A conditional step alongside a loop is the ordinary case,
                # not an impossible one. A loop outlives an unmatched gesture
                # -- `loops._shape` identifies a control by name-or-text while
                # `diff._control` uses name-or-test-id-or-css, so a keystroke
                # named in one run and only described in the other keeps its
                # position in the shape sequence while failing to pair -- and
                # the refusal above is scoped to a conditional *strictly
                # inside* the body, which is the only placement the evidence
                # genuinely cannot read. One before the block or after it
                # reaches here every time, with all three bounds moved along
                # to match.
                loops=(looped.loop,) if looped is not None else (),
            )
            # Checked against the finished version, not against `parameterisation`
            # or `steps` on their own, and that is deliberate rather than tidy:
            # `_make_room` and `_build_steps` are what fold a conditional step
            # into the paired ones, and a check that ran before them would see
            # `cod_address_id` as unfilled on the *good* four-doing case too,
            # where the address lookup survives as exactly the step that fills
            # it. Running here is running after every source of a fillable step
            # has had its say.
            _refuse_an_unfillable_input(version)
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


def _refuse_an_unfillable_input(version: SkillVersion) -> None:
    """Never hand over a version that would ask for something nothing can enter.

    The failure this whole task exists for: four real demonstrations of adding
    a carrier cross reference proved `cod_address_id` varies -- one run sent an
    address, the others sent none -- and induced a skill that asked for it
    anyway, with no step that could ever type or choose one, because the only
    doing that ever supplied the address picked it out of a dialog. A click
    with no value in it is not evidence of how the field gets filled, so
    `standing_of` drops it as noise the same way it would drop a stray click,
    and a parameter the pair genuinely proved is left standing with nothing
    behind it.

    Scoped to the *optional* inputs, deliberately, not every one -- see the
    same distinction the test file already draws with `_typed_by`. A required
    field is proven because every demonstration carried it, so the one paired
    step that always survives already sends it exactly as shown, on whichever
    medium runs the skill; there is no separate act of "choosing to supply it"
    for anything to demonstrate. An optional field is proven because some
    demonstration left it out -- and the same paired step sends it too, an
    unconditional template with `absent_as` standing in when nobody fills it,
    which is why checking `SkillStep.placeholders` here would never once fire:
    the pair's own diff always wires an optional field into that step's body
    regardless of whether anybody ever showed how to produce the value by
    hand. What that check cannot see is the thing this one is for: whether
    there is a *gesture* on record for the runs where somebody does supply it.
    `ui_plan` is where that gesture shows up -- a typed value, a chosen
    option -- and its absence, for a field the pair proved varies, is exactly
    a parameter with a demonstrated write and no demonstrated way to make one.

    Deliberately wider than the test file's own `_typed_by`: that helper reads
    only `ui_plan.value`, and this reads every name in `ui_plan.placeholders`,
    which also picks up a locator's placeholder. The two are not the same
    question answered twice by accident -- a step whose UI action is "click
    the row named `${cod_address_id}`" fills the field by choosing it on the
    screen exactly as typing it would, and the message above says as much
    ("type or choose"). `_typed_by` stays narrow because the test it guards
    is about one specific gesture that types; this check is about whether any
    gesture at all stands in for the field, which is the wider of the two
    questions and the one this refusal exists to answer.

    Inert on a single-run induction. `optional` can only be true once two
    demonstrations have disagreed about whether the field is present at all --
    see `Parameter.optional`, derived from `absent_as`, which a lone
    demonstration never sets. A parameter proposed from reading one recording
    is `Evidence.PROPOSED` and unconfirmed by design (ADR 004), and nothing
    here stands in for that confirmation; this is a guard on the paired path,
    not a general promise that every parameter this system ever proposes has
    a step behind it.

    A parameter carrying `options` is answerable and is not refused. This is
    the other half of the same question -- can whoever runs this skill produce
    the value -- and a dropdown is a way of producing it that no step's
    `ui_plan` records, because the console draws the field itself: it fetches
    the list from the endpoint the demonstration's own screen used and the
    operator picks off it exactly as they did when they taught it. Refusing
    that is refusing the answer for lacking the shape of the question.

    ponytail: `optional` is still a proxy for the rest of it, and the proxy
    has a known gap. Four doings that all pick a COD address through the same
    dialog, none blank, prove the field varies (the ids differ) without ever
    setting `absent_as`, so `optional` reads False and this refusal stays
    silent on a version that asks an operator to recite an internal id from
    memory -- which is harmless where a lookup was planned and not where one
    was not. Close it when that shape turns up in real data by finishing the
    predicate with "or the goal supplies it", rather than widening `optional`
    itself, which the two other rungs of this ladder (network-only required
    fields, and `_typed_by`'s narrower reading) already show is not a safe
    place to widen from.
    """
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
"""The answer that turns a demonstrated constant into something the operator is
prompted for. The other answer is the value itself, which changes nothing."""


def choice_key(objective: ObjectiveKey, field: str) -> str:
    """Addressed by task and field, so re-teaching finds the answer rather than
    asking again."""
    return f"{objective.target_system}/{objective.entity_type}/{objective.objective_type}/{field}"


def _wanted(parameterisation: Parameterisation) -> tuple[lookups.Wanted, ...]:
    """Every value that might have come off a list, chosen or supplied.

    A constant the operator picked twice and an id that differed between the
    two doings were picked the same way, off the same screen. Only the first
    used to be offered a lookup, so the value that varied -- the one the
    operator must supply afresh every run, and cannot type -- was the one left
    with no way to be answered. Whether the skill will vary it is a question
    about the parameter, not about where its value comes from.

    A parameter is offered when a human supplies it, has no list already, and
    the demonstrations saw a value for it. `substitutions` says which step sent
    it, which is what bounds the search for the read that showed it.

    One INPUT parameter can substitute at more than one step, so this takes the
    earliest -- the same reason `diff.py`'s `earliest_use` does. A later step is
    itself the write, or comes after it, and bounding the search there lets the
    listing search run past the write and pick up a read that came after it:
    exactly the ordering this lookup exists to get right.
    """
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
    """Give each chosen id the list it was chosen from.

    The value stays what the call needs -- the id -- and stops being something
    a person has to know: the console draws a dropdown, fills it from the same
    endpoint the screen used, and what the operator picks is what runs.

    Evidence is left alone. A choice that became a parameter is already
    `PROPOSED` where it was built; a parameter the diff produced is `PROVEN`
    because two demonstrations disagreed about it, and hanging a dropdown off
    it does not unprove that. Options say where a value comes from; evidence
    says how firmly we know it is a parameter at all.
    """
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


@dataclass(frozen=True, slots=True)
class _Conditional:
    """A step the pair did not have, and what brings it about.

    Both halves are evidence and neither is a reading: the gesture is what some
    operator did, and the parameter is the one the body diff already called
    optional at the pointer that gesture's value landed on. Most of these are
    conditional and the name has stayed; one the doings simply agree on is
    gated on nothing, and says so with a `parameter` of ``None``.
    """

    frame: ActionFrame
    at: int
    """How many paired steps come before it, so it can be put back in its place
    in the order rather than at the end of it."""

    parameter: str | None
    """The optional parameter whose presence decides whether the step happens,
    or ``None`` for a step the whole history made that the pair simply did not
    share -- part of the task on the strength of its count, gated on nothing."""


def _conditionals(
    parameterisation: Parameterisation,
    fills: tuple[OptionalFill, ...],
    *,
    promised: bool = True,
) -> tuple[_Conditional, ...]:
    """The dropped gestures that can be said to fill something, and which.

    Nothing is guessed here. The pointer the keystroke bound to has to be one
    the diff already parameterised *and* called optional; where it is not, the
    pair is refused rather than emitted, because these are exactly the gestures
    `align` excused itself from refusing. Dropping one silently is the field
    quietly becoming unfillable -- the skill still saves the form, still looks
    right, and the only gesture in either recording that fills that field is
    gone. Refusing says so, the way the pair said so before any of this existed.

    ``promised`` is what that refusal rests on. `align` stopped refusing an
    unmatched keystroke *because* `optional_fills` undertook to hand it back;
    a gesture from some third doing was never excused by anybody, so nothing
    was promised about it and there is nothing to break. One that names no
    optional field is simply a gesture the diff cannot account for, which is
    the question :func:`standing_of` answers -- and it answers `NOISE`, which
    drops it with a reason a reviewer can read rather than failing the whole
    induction over somebody's stray click in doing eleven.

    What holds is "every gesture reaching here with ``promised`` is one of the
    pair's", not the converse. `_extra_steps` recognises the pair's fills by
    ``id(fill.frame)`` against the reference, and the reference is whichever
    doing the others agreed with most -- which need not be either of the pair.
    Where it is a history run that filled the same field, the reference holds
    *that* run's frame at the position, the identity lookup misses the pair's
    own, and a fill `align` did excuse arrives here as ``loose`` with
    ``promised=False``. The refusal it should have raised is not raised.

    Left as it is because nothing harmful gets through it. The outcome the
    refusal exists to prevent -- an optional parameter with no gesture that
    can produce its value -- is caught on the finished version by
    :func:`_refuse_an_unfillable_input`, which reads the emitted steps rather
    than the frames and so does not care which object the reference happened
    to hold. What is lost is the earlier, better-worded complaint, and a
    correct outcome reported by the wrong sentence is not worth re-keying an
    identity lookup for at this distance from the evidence.
    """
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
    """Every step of the task the pair did not have, and where each belongs.

    The pair stays the spine. Everything downstream -- the parameters, the
    substitutions that carry them, the assertions, the narration, the loop's
    bounds -- is addressed by position in `align(frames_a, frames_b)`, because
    that is the one place two runs disagreed and ADR 004 says a disagreement
    between two runs is what proves a value. `align_all` is read for what the
    pair could not see: which *other* steps the doings made, and how many of
    them made each. Those come back as insertions among the paired steps,
    which is the shape a dropped gesture already came back in.

    So a step the pair shares is kept whatever its count says. Two runs
    agreeing is the standard this codebase already sets for identity, and
    :func:`standing_of` is deciding a different question -- what to do with a
    step only some doings made. Where a paired step does come out below the
    threshold that is said out loud rather than acted on, because acting on it
    means moving every index above backwards through the parameterisation, the
    parameters' sources and the loop's bounds, and nothing in hand asks for
    that.

    ponytail: dropping a paired step needs the mirror of `_moved` -- indices
    that close up rather than open out -- and a batch where a step two
    demonstrations shared is genuinely not the task. Build it when one turns
    up, not before.
    """
    frames_a = runs[0]
    spine = _reconcile(alignment, pairs, frames_a)
    # How many paired steps come before each reference position. The one
    # number that puts an insertion back in the order, and the only place the
    # two index spaces are allowed to meet.
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
            # An unmatched gesture of the pair that `optional_fills` did not
            # excuse. `align` has already had its say about this one: it
            # refused if it was evidence of anything, so what is left is a
            # click that fetched nothing and typed nothing.
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
    # Which reference position each branch sits at, so `standing_of` reads its
    # keystroke where it actually looks. This is the reconciliation doing its
    # work: without it the branch has no substitution at that index and comes
    # out `NOISE`.
    gated = {
        index: conditional.parameter
        for index, fill in (*promised, *loose)
        for conditional in conditionals
        if conditional.frame is fill.frame and conditional.parameter is not None
    }

    standing = standing_of(alignment, _at_reference(parameterisation, spine, gated))
    for index, paired in spine.items():
        if paired and standing[index] is not Standing.ALWAYS:
            # Kept anyway -- see above -- and said out loud, because "the
            # counts disagreed and nothing happened" is exactly the kind of
            # thing that is only obvious to whoever wrote it.
            logger.info(
                "keeping step %s: both demonstrations made it, though only %d of the doings did",
                ", ".join(str(step) for step in paired),
                alignment.seen[index],
            )
    for index, frame in plain:
        # Not `.get(index, ...)`: every reference position has a standing, and
        # a missing one would be a reconciliation that lost a step rather than
        # a step with nothing to say about it.
        if standing[index] is not Standing.ALWAYS:
            logger.info(
                "dropping a step %d of the doings made and nothing accounts for: %s",
                alignment.seen[index],
                frame.action.kind,
            )
            continue
        if frame.action.value or frame.action.secret or frame.primary_request is not None:
            # A step most doings made, that neither demonstration in the pair
            # made, that carried a value or changed something. Nothing diffed
            # what it sends, so emitting it replays one operator's typing on
            # every run and dropping it loses a step the counts say is the
            # task. That is the disagreement `align` refuses two runs over,
            # and it is refused here for the same reason.
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
    """Where this gesture's typing landed in the write its own doing sent.

    `_optional_pointer` asks a second question beside this one -- did the
    *other* run leave that field alone -- because for the pair that is what
    makes a field optional at all. Here it is already settled and asking again
    would answer wrongly: the field is optional because the diff proved it so,
    from the two runs it read, and a third doing that also filled it is
    evidence of nothing either way. Asked against run A, an address run A also
    filled would come back "not optional" and the branch would be dropped by
    the check meant to find it.
    """
    return next(
        (pointer for write in run if (pointer := binding.key_filled_by(frame, write)) is not None),
        None,
    )


def _reconcile(
    alignment: Alignment,
    pairs: tuple[tuple[ActionFrame, ActionFrame], ...],
    frames_a: tuple[ActionFrame, ...],
) -> dict[int, tuple[int, ...]]:
    """Which paired steps each reference step speaks for. Often none, sometimes
    several, and getting this wrong is how the address lookup is lost again.

    Two index spaces meet here and they count different things.
    :func:`standing_of` addresses a step by its position in
    ``Alignment.reference`` -- whole gestures, of whichever run the doings
    agreed with most, which need not be either run of the pair.
    :class:`Parameterisation` addresses one by its position in
    `align`'s *exploded* pairs, where a Save that sent a POST and a PUT is two
    steps and every index is run A's. They agreed only for as long as nothing
    called both. Left unreconciled, every `conditional_on` lookup would miss,
    every branch would come out `NOISE`, and the lookup would go out through a
    new door with the old door's reasoning still written above it.

    Reference to run A by :func:`_longest_common`, which is what `align_all`
    used to build the reference in the first place -- the identity pairing
    when the reference *is* run A, and the honest one when it is not. Then run
    A's frame to the paired steps that came out of it, by `frame.index`, which
    `explode` preserves when it splits one gesture's calls apart: within one
    recording that number is unique, which is what makes it safe to key on.
    """
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
    """The same parameterisation, addressed the way :func:`standing_of` reads it.

    Only the substitutions move, and only their keys: this is handed to
    `standing_of` and nowhere else, which asks one question of it --
    :meth:`Parameterisation.conditional_on`, the optional field this step's own
    keystroke types.

    The insertions get an entry too, holding exactly what `_make_room` will
    give them in the paired space. Without it a gesture that came back as a
    branch would have no substitution at the position `standing_of` looks at,
    `conditional_on` would answer `None`, and a step made by one doing in four
    would be `NOISE` -- the address lookup, dropped again, by the piece of code
    written to keep it.
    """
    optional = {parameter.name for parameter in parameterisation.parameters if parameter.optional}
    at: dict[int, list[Substitution]] = {}
    for index, paired in spine.items():
        for step in paired:
            at.setdefault(index, []).extend(parameterisation.substitutions.get(step, ()))
    for index, parameter in gated.items():
        at.setdefault(index, []).append(Substitution(site=ActionValueSite(), parameter=parameter))

    for subs in at.values():
        # `conditional_on` answers with `next`, so two keystroke sites naming
        # two optional fields at one step would be settled by whichever
        # substitution happened to sit first. `SkillStep.when` is a single
        # string and cannot say "when both were supplied"; running the step on
        # half of its condition is not a smaller wrong answer than refusing, so
        # this refuses. See `Parameterisation.conditional_on`, which names this
        # as the wiring's problem rather than its own.
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
    """Where an aligned step ends up once the conditional ones take their place.

    Every index induction produces -- a substitution's step, a parameter's
    source, a loop's body -- counts aligned steps. Inserting a step among them
    moves everything after it along, and an index left where it was would hand a
    step its neighbour's values.
    """
    return index + sum(1 for conditional in conditionals if conditional.at <= index)


def _make_room(
    parameterisation: Parameterisation, conditionals: tuple[_Conditional, ...]
) -> Parameterisation:
    """The same parameterisation, addressed to where the steps have moved to.

    The conditional steps get an entry of their own: what the operator typed is
    the value of the parameter they are conditional on, so the step sends
    ``${delta_priority}`` exactly as an aligned step would rather than replaying
    the one priority somebody happened to demonstrate.
    """
    if not conditionals:
        return parameterisation
    substitutions = {
        _moved(index, conditionals): subs for index, subs in parameterisation.substitutions.items()
    }
    for position, conditional in enumerate(conditionals):
        if conditional.parameter is None:
            # A step the counts kept and no supplied value gates. It types
            # nothing, so there is nothing to substitute into it.
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


def _build_steps(
    run_a_frames: tuple[ActionFrame, ...],
    run_b_frames: tuple[ActionFrame, ...],
    run_a: Recording,
    objective: ObjectiveKey,
    parameterisation: Parameterisation,
    conditionals: tuple[_Conditional, ...] = (),
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

    steps: list[SkillStep] = []
    pending = list(conditionals)
    for index in range(len(frames_a) + 1):
        while pending and pending[0].at <= index:
            steps.append(_emit_conditional(len(steps), pending.pop(0), parameterisation, objective))
        if index == len(frames_a):
            break
        steps.append(
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
            )
        )
    return tuple(steps)


def _emit_conditional(
    index: int,
    conditional: _Conditional,
    parameterisation: Parameterisation,
    objective: ObjectiveKey,
) -> SkillStep:
    """The gesture the pair did not share, as a step of the skill.

    With a `when` where a supplied value brings it about, and without one where
    the doings simply agree it happens.

    A gesture and nothing else -- the calls it made are dropped with the same
    reasoning as the assertions. Both would be built from one observation, and
    one observation is not two runs agreeing: whichever run did this, nothing
    diffed what it sent and every value in it would replay exactly as
    demonstrated. A form that PATCHes a draft on each keystroke would carry the
    work area of whoever was recorded into every later run of the skill.

    Nothing is lost by dropping them. If the value has to reach the system by
    call, it reaches it in the write both runs sent -- which is an aligned step,
    and already carries the parameter.
    """
    # Nothing to check, and nothing hides that. A step with no assertions
    # cannot be verified after it runs, and a skill where most steps are these
    # is a skill a review cannot tell apart from one that works -- on the four
    # real carrier recordings that is five steps of seven. The count belongs
    # where the drops already go, so a reviewer reads it rather than infers
    # it. Not repaired here: assertions built from frames nothing diffed would
    # be one observation dressed as agreement, which is the trade above.
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


def _started_on(*recordings: Recording | None) -> str | None:
    """The page every demonstration of this task opened on.

    The first frame's, because that is the screen the operator was looking at
    when they began -- not the last, which is wherever the task left them.

    Unanimous or nothing. Two demonstrations that began on different screens are
    evidence that the screen is not part of the task, and navigating on a
    disagreement would send a run somewhere only one of them ever was.
    """
    began = {
        recording.frames[0].page_url
        for recording in recordings
        if recording is not None and recording.frames and recording.frames[0].page_url
    }
    return began.pop() if len(began) == 1 else None
