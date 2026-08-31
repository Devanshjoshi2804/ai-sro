"""Skill aggregate. See docs/06-glossary.md#skill."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import PrincipalId, RecordingId, SkillId, TenantId
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.assertion import Assertion
from sro.domain.skill.earned import earned_stage
from sro.domain.skill.loop import Loop
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import NetworkPlan, ToolPlan, UiPlan
from sro.domain.skill.promotion import PromotionStage, check_promotion
from sro.domain.skill.track_record import TrackRecord, Verdict, why_not_autonomous


@dataclass(frozen=True, slots=True)
class SkillStep:
    index: int
    intent: str
    network_plan: NetworkPlan | None = None
    ui_plan: UiPlan | None = None
    tool_plan: ToolPlan | None = None
    """Somebody mapped this step onto a connector's tool. Beside the other two
    rather than instead of them: a step that can be a call, a gesture *and* a
    tool call is one a run can perform three ways, and which it took is what
    the medium on the outcome says."""
    assertions: tuple[Assertion, ...] = ()
    requires_human: bool = False

    narration: str = ""
    """What the operator said while doing this step.

    Kept apart from ``intent`` on purpose: intent is derived from what was
    observed and is the same on every replay, narration is a transcript and is
    a model's reading of a microphone. One field holding either would make them
    indistinguishable at review, which is where the difference matters most."""

    branch_hint: str | None = None
    """A path the operator described but did not demonstrate. A question for a
    reviewer -- never executed, because nothing was recorded doing it."""

    when: str | None = None
    """The parameter whose presence decides whether this step happens at all.

    A form's optional field: one demonstration typed here and the other left it
    alone, and both created the record. Supplied, the step runs; left out, it is
    skipped and the field goes over the wire the way the demonstration that
    skipped it sent it."""

    def __post_init__(self) -> None:
        if self.index < 0:
            raise InvariantViolation("SkillStep.index must be non-negative")
        if not self.intent.strip():
            raise InvariantViolation("SkillStep requires an intent")
        if self.network_plan is None and self.ui_plan is None and self.tool_plan is None:
            raise InvariantViolation(
                f"step {self.index} has no network plan, UI plan or tool plan; "
                "there is no way to perform it"
            )

    @property
    def placeholders(self) -> frozenset[str]:
        names: set[str] = set()
        if self.network_plan is not None:
            names |= self.network_plan.placeholders
        if self.ui_plan is not None:
            names |= self.ui_plan.placeholders
        if self.tool_plan is not None:
            names |= self.tool_plan.placeholders
        for assertion in self.assertions:
            names |= assertion.expected.placeholders
        return frozenset(names)


@dataclass(frozen=True, slots=True)
class Provenance:
    """Where a version came from. Never optional."""

    recording_ids: tuple[RecordingId, ...]
    """The demonstrations this version descends from.

    Descends from, not "were performed against it": a repaired version carries
    the recordings of the version it repairs, because every value it sends and
    every step but one came from them and how many there were is a live safety
    rule -- ``from_one_demonstration`` decides whether a write skill's values
    were ever diffed, and a version that dropped them would read as diffed and
    climb a rung nobody meant it to. What that field must not do is imply
    somebody demonstrated *this* version, and ``repaired_from`` below is how a
    reviewer tells the two apart without reading prose."""

    induced_at: datetime
    induced_by: PrincipalId
    """Who produced this version. ``drift-repair`` where the system did, which
    is not a person and does not pretend to be one."""

    note: str = ""

    repaired_from: str | None = None
    """The run that closed the evidence a repair adopted, where no demonstration
    produced this version at all.

    A field of its own rather than a sentence in ``note``: "was this written by
    a person or by the system" is the first question anybody asks about a
    version that changed itself, and an answer only prose can give is an answer
    no screen and no query can filter on.

    A run id as text, not a ``RunId``: an execution is a different aggregate,
    and a skill importing one to name it would point the dependency the wrong
    way round for the sake of a type.
    """

    aligned_recording_ids: tuple[RecordingId, ...] = ()
    """Which of ``recording_ids`` shaped the *steps* -- the subset ``align_all``
    actually diffed, as opposed to the ones read only for what they proved a
    parameter could be.

    The distinction this field exists to hold: a version induced from four
    demonstrations used to cite all four in ``recording_ids`` whether or not a
    given one ever touched a step, and a reader checking why a skill declared a
    parameter no step could fill had no way to see that two of the four never
    reached the steps at all -- only the parameters. Both the four and the
    fewer were true and told apart nowhere.

    A subset of ``recording_ids`` rather than a second list, so the two can
    never drift into naming different recordings by construction; the
    invariant below is what keeps that true rather than a docstring's word for
    it.

    Empty for every version induced before this field existed, and empty is
    not a claim that none of its recordings shaped the steps -- it is the
    honest admission that nobody wrote down which ones did. Reading it as
    "zero" would be the exact mistake this field was added to stop: a false
    claim standing in for missing data.

    One case a reader has to know to interpret this correctly rather than
    guess: where the pair looped, `InduceSkill` deliberately excludes the rest
    of the history from `align_all` -- see ADR 015 -- so a looping version's
    ``aligned_recording_ids`` is only the pair, never the whole of
    ``recording_ids``, on purpose. The other demonstrations are still cited,
    because they still proved parameters; they just never got a say in what
    the steps are, and this field is where that says so.
    """

    def __post_init__(self) -> None:
        if not self.recording_ids:
            raise InvariantViolation("a skill version must cite the recordings it came from")
        if self.induced_at.tzinfo is None:
            raise InvariantViolation("Provenance.induced_at must be timezone-aware")
        if not set(self.aligned_recording_ids) <= set(self.recording_ids):
            raise InvariantViolation(
                "Provenance.aligned_recording_ids must be a subset of recording_ids -- a "
                "recording cannot have shaped the steps without being cited as a source at all"
            )


@dataclass(eq=False)
class SkillVersion:
    """One revision. Steps and parameters are fixed; only the stage moves."""

    version: int
    steps: tuple[SkillStep, ...]
    parameters: tuple[Parameter, ...]
    provenance: Provenance
    stage: PromotionStage = PromotionStage.RECORDED
    promoted_at: datetime | None = None
    promoted_by: PrincipalId | None = None

    promoted_from: str = ""
    """Where the review that put this version at its current stage happened.
    Every writer names itself, so blank means exactly one thing: nobody has.

    - `"console"` -- somebody sitting down with the evidence, through
      `PromoteSkill`.
    - `"preview"` -- an operator reading the steps and the values in the
      panel and pressing once, at the screen it will act on, with a stop
      button in front of them.
    - `"earned"` -- `earn()`. Not a review at all: the streak did it, and
      nobody was asked. Kept apart from blank for the same reason
      `promoted_by` is `None` here rather than some system principal -- a
      streak is a basis, and writing nothing would make it indistinguishable
      from a version nobody has looked at.
    - `"repair"` -- `repair_drift`'s inherited climb back to the rung the
      version it replaced had earned. Mechanical, not a person's read of this
      version; the person is `REPAIR`, the review is nobody's.
    - `""` -- `demote()`, disambiguated by `demotion_reason` rather than by
      this field; the three places a version is reset to `RECORDED` for a
      fresh review (`map_step_to_tool`, `add_assertion`, `repair_drift`'s new
      version before it climbs back up); and every row written before this
      field existed.

    `"console"` and `"preview"` are both reviews, and the second is a real
    reading of what the ladder asks for -- but they are not the same review,
    and somebody auditing a library has to be able to tell them apart and
    disagree with one of them. A value that has to be decoded by joining it
    to `promoted_by` or `stage` is not one a reviewer can filter a list by,
    which is why every writer, including the ones with no human in them,
    names itself rather than leaving blank to mean more than one thing.
    """

    track_record: TrackRecord = field(default_factory=TrackRecord)
    """What this version has actually done. Autonomy is earned from this, never
    granted by a click."""

    summary: str = ""
    """What this version does, in a sentence."""

    demotion_reason: str | None = None
    """Why this version was pulled back down, when it was."""

    starts_on: str | None = None
    """The page the task was demonstrated on.

    A skill taught by clicking names no URL on any step, so a run could only be
    performed by an operator who had already navigated to the right screen --
    and one who had not got the same thirteen `control_not_found` lines as one
    whose browser was on the wrong system entirely. This is what the recorder
    saw, on the frame the demonstration opened with.

    Only where every demonstration of the task began on the same screen. Two
    that began on different ones are saying the screen is not part of the task,
    and a run that navigated on that evidence would be guessing.
    """

    systems: tuple[str, ...] = ()
    """Every system this version touches, derived from what it was taught on.

    Here rather than on the objective key, and the difference matters: the key
    is compared for equality, and that comparison is what pairs two
    demonstrations of one task. One stray host in one of them -- an identity
    provider, a CDN that answered once -- would make two keys unequal, and the
    pair would silently never pair.

    Empty for everything taught before this existed, which is what they were: a
    version that touches one system says so with `target_system` alone.
    """

    loops: tuple[Loop, ...] = ()
    """Blocks of steps the task does once per thing in a list.

    Empty for every skill taught before this existed, and for most after: a loop
    is only ever recorded where two demonstrations did the same block a
    different number of times and the system's own answer said how many.
    """

    when_to_use: str = ""
    """When to reach for it.

    Together with ``summary`` this is what an operator's request is matched
    against, so it is editable: a skill described in words nobody searches with
    is a skill nobody finds. Editing it changes what is found, never what runs.
    """

    def __post_init__(self) -> None:
        if self.version < 1:
            raise InvariantViolation("version numbers start at 1")
        if not self.steps:
            raise InvariantViolation("a skill version needs at least one step")
        self._check_step_indices()
        self._check_parameters_declared()
        self._check_derived_ordering()
        self._check_loops()

    @property
    def inputs(self) -> tuple[Parameter, ...]:
        """The values somebody has to supply for a run to be worth starting.

        Optional ones are not among them. A demonstration proved the warehouse
        accepts the record without that field and `absent_as` records exactly
        what it sent instead, so a run with nothing in it is a run that does
        what that demonstration did -- not one that fails.

        This was every INPUT parameter, which made a skill with any optional
        field impossible to put on a trigger at all: `CreateTrigger` demanded a
        value for the four boxes an operator had deliberately left empty, and
        the only way past it was to invent one.
        """
        return tuple(p for p in self.parameters if p.kind is ParameterKind.INPUT and not p.optional)

    def describe(self, *, summary: str, when_to_use: str) -> None:
        """Reword what this version is for. A label, never a behaviour."""
        if not summary.strip():
            raise InvariantViolation("a skill nobody can describe is a skill nobody will find")
        self.summary = summary.strip()
        self.when_to_use = when_to_use.strip()

    @property
    def crosses_systems(self) -> bool:
        """Whether performing this version touches more than one system.

        Such a version is performed only in a browser that is signed in to all
        of them -- the operator's own -- because this deployment holds one
        session per system and never two at once.
        """
        return len(self.systems) > 1

    @property
    def changes_the_system(self) -> bool:
        """Whether performing this version writes anything.

        A tool call counts when whoever mapped it said it writes. Nothing else
        can say: MCP declares no such thing and a tool named `send_message` is
        a name, not a promise -- so this reads the decision rather than the
        word.
        """
        return any(_writes(step) for step in self.steps)

    @property
    def from_one_demonstration(self) -> bool:
        """Induced from a single run, so nothing was diffed.

        Every value in it is the value that run happened to send. That is a
        legitimate skill -- it replays one act exactly -- and it is a different
        thing from a skill whose constants were held across two runs.

        A repaired version answers this the same way the version it repairs
        does, which is why it keeps that version's recordings: what changed was
        one locator, and every value it sends is still the value those
        demonstrations carried.
        """
        return len(self.provenance.recording_ids) == 1

    @property
    def needs_a_person(self) -> bool:
        """Whether some step can only be performed as a gesture.

        A step with no network plan is a click or a keystroke, and `judge`
        makes any run that performs one DEGRADED -- a medium that is not
        NETWORK, by the rule that a gesture means the recorded call no longer
        works. DEGRADED resets the clean streak, so such a version cannot
        accumulate one and can never reach the top of the ladder.

        That is a fact about the skill rather than about how it has been going,
        and it is the difference between "not yet" and "not ever". Somebody
        watching the streak sit at zero deserves to be told which one they are
        looking at.
        """
        return any(step.network_plan is None and step.tool_plan is None for step in self.steps)

    @property
    def unchecked_writes(self) -> tuple[int, ...]:
        """The steps that change the system and prove nothing about the result.

        A write whose two demonstrations returned different statuses and shared
        no stable response field comes out of induction with no post-condition
        at all. Performing it can then only fail by not being sent -- the
        warehouse can reject it, ignore it, or do something else entirely, and
        the run says the step was fine.
        """
        return tuple(step.index for step in self.steps if _writes(step) and not step.assertions)

    @property
    def not_ready_for_autonomy(self) -> str | None:
        """Why this version may not run unattended, or ``None`` when it may.

        Here rather than at each caller, because there were three of them and
        they disagreed: the console passed everything and the promotion gate
        passed only `verifiable`, so a version refused at the gate was told
        "no step of this skill cannot be checked" -- a sentence that is not
        even wrong. What refuses a promotion and what a screen says about it
        have to be the same sentence.
        """
        return why_not_autonomous(
            self.track_record,
            verifiable=self.verifiable,
            needs_a_person=self.needs_a_person,
            unchecked_writes=(
                "step " + ", ".join(str(index) for index in self.unchecked_writes)
                if self.unchecked_writes
                else "no step"
            ),
        )

    @property
    def verifiable(self) -> bool:
        """Whether a run of this can be checked.

        Two conditions, because one was not enough. Something must be checked
        at all -- a skill with no assertion anywhere produces runs that only
        ever prove a request was sent. And every step that *changes* the system
        must be among the checked: this was `any`, so a version whose read step
        asserted and whose writes did not counted as verified on the strength
        of the one step nobody is worried about.

        Either way it may run assisted forever; it may never run unattended.
        """
        return any(step.assertions for step in self.steps) and not self.unchecked_writes

    def record_run(
        self, verdict: Verdict, at: datetime, *, revising: Verdict | None = None
    ) -> None:
        """Count a finished run against this version.

        `revising` names a verdict this same run has already been counted
        under, and replaces it rather than adding beside it -- see
        `TrackRecord.instead_of`. `CallRunWrong` is the only caller that has
        one: it judges a run `FinishRun` finished and judged minutes earlier.
        """
        self.track_record = (
            self.track_record.after(verdict, at)
            if revising is None
            else self.track_record.instead_of(revising, verdict, at)
        )

    def earn(self, verdict: Verdict, at: datetime) -> PromotionStage | None:
        """Move up if the record now says so. Returns the rung, or None.

        Promotion by hand made a version's stage a fact about somebody's
        afternoon rather than about the skill: the ladder was always meant to be
        earned, and waiting for a click is not evidence. Nobody is named as the
        promoter because nobody was asked -- the runs were.
        """
        target = earned_stage(
            current=self.stage,
            record=self.track_record,
            verdict=verdict,
            has_verifiable_outcome=self.verifiable,
            sends_writes=self.changes_the_system,
            values_are_fixed=self.from_one_demonstration,
        )
        if target is None:
            return None
        self.stage = target
        self.promoted_at = at
        self.promoted_by = None
        self.promoted_from = "earned"
        self.demotion_reason = None
        return target

    def demote(self, to: PromotionStage, at: datetime, why: str) -> None:
        """Pull a version back down. Not a promotion in reverse: this happens
        automatically, without a human, which is exactly why it is a separate
        method with a reason attached."""
        if to.rung >= self.stage.rung:
            raise InvariantViolation(f"{to} is not below {self.stage}")
        self.stage = to
        self.promoted_at = at
        self.promoted_by = None
        self.promoted_from = ""
        self.demotion_reason = why

    def promote(
        self,
        to: PromotionStage,
        at: datetime,
        by: PrincipalId,
        *,
        acknowledging_fixed_values: bool = False,
        from_where: str = "",
    ) -> None:
        check_promotion(self.stage, to)
        if from_where == "preview" and to.rung > PromotionStage.ASSISTED.rung:
            # The argument for a preview being a review is that the operator
            # read what this run would do. Nobody reads what ten future
            # unattended runs will do.
            raise InvariantViolation(
                "a preview promotes no further than assisted; "
                f"{to} is earned by clean runs, not by a press"
            )
        if from_where == "preview" and self.demotion_reason:
            # The ladder's own backstop, protected from the press that would
            # undo it. A version is only ever carrying a `demotion_reason`
            # because it failed three runs in a row and was pulled back
            # automatically -- and the one thing that must not put it straight
            # back is the same kind of press that was failing. Without this, a
            # task that is wrong every single time never stays demoted: it is
            # demoted on the third wrong run and restored by the operator's
            # very next press, forever.
            #
            # The refusal is a sentence an operator reads, not a field name,
            # because this is raised through `RunFromPreview` and lands in the
            # panel beside the button they just pressed. What it asks for is
            # the rung the ladder exists to provide: somebody sitting down in
            # the console with the evidence -- the failed runs, the steps, the
            # assertions -- rather than somebody mid-task reading a preview of
            # the one run in front of them. A console promotion clears
            # `demotion_reason` below, which is what lets the version run
            # again, and that is exactly the person this refusal holds out for.
            raise InvariantViolation(
                "this task went wrong three times in a row, so it was pulled back and stopped "
                "running. Somebody needs to look at what it did before it runs again -- ask "
                "whoever looks after these tasks to check it in the console"
            )
        if (
            to.rung > PromotionStage.SHADOW.rung
            and self.from_one_demonstration
            and self.changes_the_system
            and not acknowledging_fixed_values
        ):
            # Shadow is where an unpaired write belongs by default: it produces
            # the request and withholds it, which is exactly what a reviewer
            # needs to see. Above that it is sent, and every send is the same
            # send -- one demonstration had nothing to diff against, so the
            # values are the ones that run happened to carry. Creating the same
            # record twice is the polite failure; the impolite one is a skill
            # that quietly writes to the same id every night.
            raise InvariantViolation(
                "this version came from one demonstration, so every value it sends is fixed "
                "as demonstrated -- running it assisted repeats that exact write. Teach it a "
                "second time to turn those values into parameters, or promote it again saying "
                "you have read what it sends"
            )
        if to is PromotionStage.AUTONOMOUS and (refusal := self.not_ready_for_autonomy):
            raise InvariantViolation(f"not ready to run unattended: {refusal}")
        if at.tzinfo is None:
            raise InvariantViolation("promotion timestamp must be timezone-aware")
        self.stage = to
        self.promoted_at = at
        self.promoted_by = by
        self.promoted_from = from_where
        # The count that demoted it, cleared by the person who looked -- and
        # only by them.
        #
        # `should_demote` is a standing condition rather than an event: it is
        # re-asked after every run, so a version demoted at three failures went
        # straight back down on its next run whatever that run did -- and it
        # could not do better, because shadow withholds the writes a clean run
        # would need. Promoting it was futile and looked like a bug in the
        # ladder. The streak is left alone: it is progress towards autonomy and
        # nobody may grant it by pressing a button.
        #
        # A preview promotion is not that person. The clearing was written for
        # a console promotion, where somebody sat down with the failures and
        # decided they were understood; the operator pressing `Do it` mid-task
        # has read the steps and the values of the one run in front of them and
        # nothing at all about the runs that failed before it. Clearing the
        # count on their behalf would hand every failing version a fresh three
        # lives on every press, which is the same hole the refusal above closes
        # from the other side -- that one stops a version that has already been
        # demoted from being put back, this one stops a version from never
        # being demoted in the first place. Both are needed: a version sitting
        # at one or two failures carries no `demotion_reason` for the refusal
        # above to catch, so a press that cleared the count would walk it back
        # to zero and the third failure would never arrive.
        if from_where != "preview":
            self.track_record = replace(self.track_record, consecutive_failures=0)
            self.demotion_reason = None

    def _check_step_indices(self) -> None:
        indices = [step.index for step in self.steps]
        if indices != list(range(len(self.steps))):
            raise InvariantViolation(f"step indices must be 0..n-1, got {indices}")

    def _check_parameters_declared(self) -> None:
        names = [p.name for p in self.parameters]
        if len(names) != len(set(names)):
            raise InvariantViolation("parameter names must be unique within a version")

        declared = set(names)
        for step in self.steps:
            # ``when`` names a parameter the same way a template does, and an
            # undeclared one is the same bug: a step conditional on something
            # nobody can supply is a step that never happens.
            named = step.placeholders | ({step.when} if step.when else frozenset())
            missing = named - declared
            if missing:
                raise InvariantViolation(
                    f"step {step.index} references undeclared parameters: "
                    f"{', '.join(sorted(missing))}"
                )

    def _check_loops(self) -> None:
        covered: set[int] = set()
        declared = {parameter.name for parameter in self.parameters}
        for loop in self.loops:
            if loop.last_step >= len(self.steps):
                raise InvariantViolation(
                    f"a loop covers steps {loop.first_step}-{loop.last_step}, "
                    f"and this version has {len(self.steps)}"
                )
            body = set(loop.body)
            if body & covered:
                # Nested and overlapping loops are refused rather than
                # supported: what they would mean at run time is a decision
                # nobody has had to make yet, and a version that means two
                # things is worse than one that refuses to exist.
                raise InvariantViolation("loops may not overlap")
            covered |= body
            unknown = sorted({binding.parameter for binding in loop.binds} - declared)
            if unknown:
                raise InvariantViolation(
                    f"a loop binds undeclared parameters: {', '.join(unknown)}"
                )

    def loop_at(self, step_index: int) -> Loop | None:
        """The loop whose body this step belongs to, if any."""
        return next((loop for loop in self.loops if loop.covers(step_index)), None)

    def loop_from(self, step_index: int) -> Loop | None:
        """The loop this step's response feeds, if any. Read when the step
        finishes, because that is the moment the list -- and so the count of
        iterations -- exists at all."""
        return next((loop for loop in self.loops if loop.over_step_index == step_index), None)

    def _check_derived_ordering(self) -> None:
        for param in self.parameters:
            source = param.source_step_index
            if param.kind is not ParameterKind.DERIVED or source is None:
                continue
            if source >= len(self.steps):
                raise InvariantViolation(
                    f"derived parameter {param.name!r} names step {source}, which does not exist"
                )
            first_use = next((s.index for s in self.steps if param.name in s.placeholders), None)
            if first_use is not None and first_use <= source:
                raise InvariantViolation(
                    f"derived parameter {param.name!r} is used at step {first_use} "
                    f"but only produced at step {source}"
                )


@dataclass(eq=False)
class Skill:
    id: SkillId
    tenant_id: TenantId
    objective_key: ObjectiveKey
    name: str
    created_at: datetime
    _versions: list[SkillVersion] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvariantViolation("Skill requires a name")
        if self.created_at.tzinfo is None:
            raise InvariantViolation("Skill.created_at must be timezone-aware")

    @property
    def versions(self) -> tuple[SkillVersion, ...]:
        return tuple(self._versions)

    @property
    def latest(self) -> SkillVersion:
        if not self._versions:
            raise InvariantViolation(f"skill {self.id} has no versions")
        return self._versions[-1]

    @property
    def runnable(self) -> SkillVersion | None:
        """The newest version something may actually be asked to run.

        A second demonstration lands at RECORDED, which the runner refuses, and
        matching always offered the newest version there was -- so re-teaching a
        working skill took it offline: every match answered with a version that
        could not run, and the only way back was to promote the new one.

        Falls back to nothing rather than to the newest: a skill with no
        runnable version is a skill nobody should be offered.
        """
        for version in reversed(self._versions):
            if version.stage is not PromotionStage.RECORDED:
                return version
        return None

    def version(self, number: int) -> SkillVersion:
        for candidate in self._versions:
            if candidate.version == number:
                return candidate
        raise InvariantViolation(f"skill {self.id} has no version {number}")

    def next_version_number(self) -> int:
        return len(self._versions) + 1

    def add_version(self, version: SkillVersion) -> None:
        """Append. Existing versions are never mutated by a re-induction."""
        expected = self.next_version_number()
        if version.version != expected:
            raise InvariantViolation(
                f"versions are append-only and sequential: expected v{expected}, "
                f"got v{version.version}"
            )
        if version.stage is not PromotionStage.RECORDED:
            raise InvariantViolation("a new version always starts at RECORDED")
        self._versions.append(version)


def _writes(step: SkillStep) -> bool:
    """Whether performing this step changes something outside this system.

    One definition, because three rules read it -- whether a version writes at
    all, which of its steps go unchecked, and what a run below the assisted
    rung is allowed to send. They disagreed once already.
    """
    if step.network_plan is not None and step.network_plan.is_mutation:
        return True
    return step.tool_plan is not None and step.tool_plan.writes
