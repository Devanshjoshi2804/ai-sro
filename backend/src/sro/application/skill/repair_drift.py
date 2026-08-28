"""A skill adopting what one of its own verified runs proved about a control.

``LearnFromRun`` already writes down that *control X is found by Y, not by the Z
it was taught with*, and stops there on purpose -- the comment there is about
Healenium, which rewrites a locator on a test that may assert nothing. That
caution does not apply to a verified run of this system, and the difference is
the whole of ``docs/superpowers/specs/2026-08-28-a-skill-that-repairs-itself``:

- **It asserted.** The run's steps proved the outcome the demonstration proved.
- **Nothing is rewritten.** A repair appends a version beside the old one, so
  reverting is promoting the older one again.
- **It re-earns its autonomy, not its right to work.** The repaired version
  inherits the rung it was already trusted at, capped below ``AUTONOMOUS``, and
  starts with an empty record. Surviving one run is not ten clean ones; it is
  also not a reason to stop doing the job a person is still authorising.

Only the drifted step changes. Every other step is the same object as before,
because a repair is the old version with one plan replaced -- never a fresh
induction of a skill nobody demonstrated again.

A vision-sourced repair writes no version at all. At the interface rung the
control was found by the application's own structure; at the vision rung a model
read pixels and chose, and letting that write the skill is a model marking its
own homework. So it becomes a question for a person, asked once.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from sro.application.context import RequestContext
from sro.application.knowledge.open_questions import Ambiguity, AskAbout
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.execution.run import Medium, Run, RunStatus, StepDisposition, StepOutcome
from sro.domain.shared.identifiers import PrincipalId
from sro.domain.skill.locator import ControlLocator
from sro.domain.skill.plan import UiPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep, SkillVersion
from sro.domain.skill.track_record import TrackRecord

REPAIR = PrincipalId("drift-repair")
"""Named as the promoter of a repaired version, because something has to be.

Not a person, and it does not pretend to be one: the person is whoever
authorises the next run, which at every rung a repair can reach is still
somebody. What this records is that the rung was inherited rather than earned by
runs or granted by a click.
"""


@dataclass(frozen=True, slots=True)
class Drift:
    """One step that was performed by something other than what it was taught."""

    step: SkillStep
    plan: UiPlan
    taught: ControlLocator
    matched: str

    @property
    def worked(self) -> ControlLocator | None:
        """The locator this step already carries that actually found the control.

        ``None`` where nothing it carries did -- which is what the vision rung
        records, and the one case a person has to answer.
        """
        return next((loc for loc in self.plan.locators if loc.strategy.value == self.matched), None)


class RepairDrift:
    """Adopt, into a new version, the locator a verified run actually used."""

    def __init__(self, uow: UnitOfWork, clock: Clock, ask: AskAbout) -> None:
        self._uow = uow
        self._clock = clock
        self._ask = ask

    async def execute(self, ctx: RequestContext, *, run: Run) -> int | None:
        """The new version's number, or ``None`` when nothing drifted.

        A run whose assertions failed proves the skill and the system disagree,
        and which of the two is wrong is exactly what it does not establish.
        """
        if run.status is not RunStatus.SUCCEEDED:
            return None

        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)
            version = skill.version(run.skill_version)
            if version is not skill.latest:
                # Somebody has taught this since the run started. Their version
                # is later evidence than this run, and appending a repair of an
                # older one would put it in front of theirs.
                return None

            # By step, not by outcome: a loop's body occupies as many
            # positions as there were things in the list, and one control that
            # moved is one repair however many times it was clicked.
            drifts = {
                found.step.index: found
                for outcome in run.steps
                if (found := _drift(version, outcome))
            }
            repaired = {
                i: _trying_first(d, worked)
                for i, d in drifts.items()
                if (worked := d.worked) is not None
            }

            for drift in drifts.values():
                if drift.worked is None:
                    await self._ask.raise_question(
                        ctx,
                        _question(
                            drift,
                            run=run,
                            system=skill.objective_key.target_system,
                            skill_name=skill.name,
                            version=version,
                        ),
                    )

            if not repaired:
                return None

            now = self._clock.now()
            fresh = replace(
                version,
                version=skill.next_version_number(),
                steps=tuple(repaired.get(step.index, step) for step in version.steps),
                # Appended where every version is appended. The rung it
                # inherits is set below, once it is on the skill.
                stage=PromotionStage.RECORDED,
                # None of the old one's record: the climb back to unattended
                # starts at zero, because one run is not ten.
                track_record=TrackRecord(),
                promoted_at=None,
                promoted_by=None,
                demotion_reason=None,
                provenance=replace(
                    version.provenance,
                    induced_at=now,
                    induced_by=run.requested_by,
                    note=_note(run, version, tuple(drifts.values())),
                ),
            )
            skill.add_version(fresh)
            # `Skill.runnable` serves the newest version that is not RECORDED,
            # so this one takes over from the one it repairs the moment it is
            # saved -- and a version that took over at SHADOW would withhold
            # every write. A skill that repaired itself would stop doing the
            # work, which is the opposite of healing.
            #
            # So it inherits the rung, capped below AUTONOMOUS. At ASSISTED a
            # named person authorises every run; that person is the safety, and
            # they are still there, looking at a version that differs from the
            # one they were happily running by a single locator a verified run
            # proved. Unattended is the one rung nobody is watching, so it is
            # the one a repair may not inherit: a version nobody has watched
            # re-earns the right to act unwatched, from the empty record above.
            inherited = (
                version.stage
                if version.stage.rung < PromotionStage.AUTONOMOUS.rung
                else PromotionStage.ASSISTED
            )
            while fresh.stage.rung < inherited.rung:
                # Through `promote`, one rung at a time, rather than assigning
                # the stage behind the guard's back -- and with the truthful
                # promoter and the run's clock. `acknowledging_fixed_values`
                # says what is true of an inherited rung: a fixed-value write
                # skill only reaches ASSISTED because somebody read what it
                # sends, and this version sends the same thing.
                fresh.promote(
                    fresh.stage.next_stage(), now, REPAIR, acknowledging_fixed_values=True
                )
            await uow.skills.save(skill)
            await uow.commit()
            return fresh.version


def _drift(version: SkillVersion, outcome: StepOutcome) -> Drift | None:
    if outcome.medium not in (Medium.UI, Medium.VISION):
        return None
    if outcome.disposition is not StepDisposition.PERFORMED or outcome.assertion_failures:
        return None
    if outcome.step_index >= len(version.steps):
        return None
    step = version.steps[outcome.step_index]
    plan = step.ui_plan
    if plan is None or not plan.locators:
        return None
    taught = plan.locators[0]
    if outcome.matched_by is None or outcome.matched_by == taught.strategy.value:
        return None
    return Drift(step=step, plan=plan, taught=taught, matched=outcome.matched_by)


def _trying_first(drift: Drift, worked: ControlLocator) -> SkillStep:
    """The same step, with the locator that worked tried first.

    The others are kept, in order, behind it: they resolved on the day this was
    demonstrated, and a screen that changes back is not a screen this skill
    should have to be taught twice.
    """
    others = tuple(loc for loc in drift.plan.locators if loc is not worked)
    return replace(drift.step, ui_plan=replace(drift.plan, locators=(worked, *others)))


def _question(
    drift: Drift, *, run: Run, system: str, skill_name: str, version: SkillVersion
) -> Ambiguity:
    return Ambiguity(
        system=system,
        key=f"control {drift.taught.describe()} was not found where it was taught",
        question=(
            f"{drift.taught.describe()} was reached by {drift.matched} rather than by the "
            f"{drift.taught.strategy.value} this skill was taught with. Where is it now?"
        ),
        options=("demonstrate the step again", "leave the skill as it is and keep escalating"),
        because=(
            f"run {run.id.value} of {skill_name} v{version.version} step {drift.step.index} "
            f"finished the step, but only by {drift.matched}",
        ),
    )


def _note(run: Run, version: SkillVersion, drifts: tuple[Drift, ...]) -> str:
    """Why this version exists, in the words the console shows.

    A skill that quietly rewrites itself is one nobody can trust, so the run
    that proved the change is named in the provenance rather than only in a log.
    """
    changes = ", ".join(
        f"step {d.step.index} is found by {d.matched} rather than the "
        f"{d.taught.strategy.value} it was taught with"
        for d in drifts
        if d.worked is not None
    )
    return (
        f"repaired from run {run.id.value}, which verified v{version.version}: {changes}. "
        "Nobody demonstrated this again; every other step is the one that run performed."
    )
