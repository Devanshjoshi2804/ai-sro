"""A skill adopting what its own verified runs have agreed about a control.

``LearnFromRun`` already writes down that *control X is found by Y, not by the Z
it was taught with*, and stops there on purpose -- the comment there is about
Healenium, which rewrites a locator on a test that may assert nothing. That
caution does not apply to the knowledge store's settled answer, and the
difference is the whole of
``docs/superpowers/specs/2026-08-28-a-skill-that-repairs-itself``:

- **It asserted, and more than once.** A repair reads the store, not the run it
  is triggered by. One escalation is a slow page, a race, a modal that was still
  open; ``SETTLED`` verified runs agreeing is a control that moved.
- **Nothing is rewritten.** A repair appends a version beside the old one, so
  reverting is promoting the older one again.
- **It re-earns its autonomy, not its right to work.** The repaired version
  inherits the rung it was already trusted at, capped below ``AUTONOMOUS``, and
  starts with an empty record. Surviving one run is not ten clean ones; it is
  also not a reason to stop doing the job a person is still authorising.

Only the drifted step changes. Every other step is the same object as before,
because a repair is the old version with one plan replaced -- never a fresh
induction of a skill nobody demonstrated again.

Where the evidence cannot name a locator this step carries, no version is
written and a person is asked. That covers the vision rung -- a model read
pixels and chose, and letting that write the skill is a model marking its own
homework -- and it covers a plan carrying two locators of the strategy the
evidence names, where adopting one of them would be a guess about which.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, replace
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.knowledge.open_questions import Ambiguity, AskAbout
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.execution.run import Run, RunStatus
from sro.domain.knowledge.entry import SUPPORTS_AUTOMATION, EntryKind, KnowledgeEntry
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import PrincipalId
from sro.domain.skill.locator import ControlLocator
from sro.domain.skill.plan import UiPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill, SkillStep, SkillVersion
from sro.domain.skill.track_record import TrackRecord

REPAIR = PrincipalId("drift-repair")
"""Named as the author and the promoter of a repaired version, because nobody
else is. Not a person, and it does not pretend to be one: the person is whoever
authorises the next run, which at every rung a repair can reach is still
somebody. What this records is that no demonstration produced this version."""

SETTLED = 3
"""How many verified runs have to agree before a drift is adopted.

Once is noise -- a page that had not settled, a modal still closing, a race
between a render and a click -- and a version rewritten on one escalation is a
version rewritten by a bad afternoon. Twice is a coincidence, which is the same
number and the same reasoning as ``WORTH_OFFERING``: this system has counted
three doings before offering a task since the day it started counting anything,
and a repair is a larger claim than an offer, not a smaller one.

Three is also what makes the chain terminate. The store is asked for the last
three claims about the control; once the repair is adopted the step leads with
the locator that worked, later runs find it where they were taught, and the
claims stop saying it drifted. A drift is adopted once, not once per run.
"""


@dataclass(frozen=True, slots=True)
class Drift:
    """One step whose control the store says is no longer where it was taught."""

    step: SkillStep
    plan: UiPlan
    taught: ControlLocator
    matched: str

    @property
    def worked(self) -> ControlLocator | None:
        """The one locator this step carries that the evidence names.

        ``None`` where nothing it carries does -- which is what the vision rung
        records -- and ``None`` where two of them do. The evidence names a
        *strategy*, not a locator, so a plan holding two CSS paths cannot say
        which of them the driver used, and promoting the first of them is how a
        destructive control ends up tried ahead of the one that worked. Both are
        a question for a person rather than a guess.
        """
        found = [
            locator for locator in self.plan.locators if locator.strategy.value == self.matched
        ]
        return found[0] if len(found) == 1 else None


class RepairDrift:
    """Adopt, into a new version, the locator the store's evidence has settled on."""

    def __init__(self, uow: UnitOfWork, clock: Clock, ask: AskAbout) -> None:
        self._uow = uow
        self._clock = clock
        self._ask = ask

    async def execute(self, ctx: RequestContext, *, run: Run) -> int | None:
        """The new version's number, or ``None`` when nothing has settled.

        Triggered by a run that finished, and decided by what every run before
        it wrote down. A run whose assertions failed proves the skill and the
        system disagree, and which of the two is wrong is exactly what it does
        not establish -- so it is not even a reason to look.
        """
        if run.status is not RunStatus.SUCCEEDED:
            return None

        number: int | None = None
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)
            version = skill.version(run.skill_version)
            if version is not skill.latest:
                # Somebody has taught this since the run started. Their version
                # is later evidence than anything here, and appending a repair
                # of an older one would put it in front of theirs.
                return None

            drifts = tuple(
                [
                    drift
                    async for drift in self._drifted(
                        ctx, uow, version, system=skill.objective_key.target_system
                    )
                ]
            )
            repaired = {
                drift.step.index: _trying_first(drift, worked)
                for drift in drifts
                if (worked := drift.worked) is not None
            }
            if repaired:
                number = _adopt(skill, version, run, repaired, drifts, at=self._clock.now())
                await uow.skills.save(skill)
                try:
                    await uow.commit()
                except Conflict:
                    # Two runs finished together, or a demonstration landed
                    # while this was reading. Whoever got there first wrote a
                    # version this one has not seen, and appending on top of a
                    # skill that has moved is how one of two repairs disappears
                    # with a green log to show for it. The store still says the
                    # control drifted, so the next run adopts it.
                    return None

        # Outside the transaction: `AskAbout` opens its own unit of work, and
        # entering the same one twice leaves the outer block without a session.
        for drift in drifts:
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
        return number

    async def _drifted(
        self, ctx: RequestContext, uow: UnitOfWork, version: SkillVersion, *, system: str
    ) -> AsyncIterator[Drift]:
        """Every step of this version whose control the store has settled on."""
        for step in version.steps:
            plan = step.ui_plan
            if plan is None or not plan.locators:
                continue
            taught = plan.locators[0]
            matched = _settled(
                await uow.knowledge.history(
                    ctx.tenant_id,
                    system=system,
                    kind=EntryKind.SCREEN,
                    # The same key `LearnFromRun` writes: the control, not the
                    # skill. Two skills clicking one button are two observations
                    # of where that button is.
                    key=f"control {taught.describe()}",
                    limit=SETTLED,
                )
            )
            if matched is not None:
                yield Drift(step=step, plan=plan, taught=taught, matched=matched)


def _settled(entries: tuple[KnowledgeEntry, ...]) -> str | None:
    """What the store says found this control, where it has stopped changing.

    ``None`` unless the last ``SETTLED`` claims about it are all from separate
    verified runs, all say it drifted, and all name the same thing as having
    found it. Anything less is one run's opinion, and a version is not rewritten
    on one run's opinion.
    """
    if len(entries) < SETTLED:
        return None
    if len({entry.source for entry in entries}) < SETTLED:
        return None
    if any(entry.evidence.rank < SUPPORTS_AUTOMATION.rank for entry in entries):
        return None
    if not all(entry.body.get("drifted") is True for entry in entries):
        return None
    found = {str(entry.body.get("found_by")) for entry in entries}
    return found.pop() if len(found) == 1 else None


def _adopt(
    skill: Skill,
    version: SkillVersion,
    run: Run,
    repaired: dict[int, SkillStep],
    drifts: tuple[Drift, ...],
    *,
    at: datetime,
) -> int:
    """Append the repaired version and walk it to the rung it inherits."""
    fresh = replace(
        version,
        version=skill.next_version_number(),
        steps=tuple(repaired.get(step.index, step) for step in version.steps),
        # Appended where every version is appended. The rung it inherits is set
        # below, once it is on the skill.
        stage=PromotionStage.RECORDED,
        # None of the old one's record: the climb back to unattended starts at
        # zero, because agreeing runs are not clean ones.
        track_record=TrackRecord(),
        promoted_at=None,
        promoted_by=None,
        demotion_reason=None,
        provenance=replace(
            version.provenance,
            # `induced_by` was the requester of the proving run, which read as
            # a person having produced this. Nobody did, and `repaired_from` is
            # what says so somewhere a screen can filter on rather than only in
            # the sentence below. The recordings stay: they are what every value
            # this version sends still came from, and dropping them would make a
            # fixed-value write skill read as one that had been diffed.
            repaired_from=run.id.value,
            induced_at=at,
            induced_by=REPAIR,
            note=_note(run, version, drifts),
        ),
    )
    skill.add_version(fresh)
    # `Skill.runnable` serves the newest version that is not RECORDED, so this
    # one takes over from the one it repairs the moment it is saved -- and a
    # version that took over at SHADOW would withhold every write. A skill that
    # repaired itself would stop doing the work, which is the opposite of
    # healing.
    #
    # So it inherits the rung, capped below AUTONOMOUS. At ASSISTED a named
    # person authorises every run; that person is the safety, and they are still
    # there, looking at a version that differs from the one they were happily
    # running by a single locator several verified runs proved. Unattended is
    # the one rung nobody is watching, so it is the one a repair may not
    # inherit: a version nobody has watched re-earns the right to act unwatched,
    # from the empty record above.
    inherited = (
        version.stage
        if version.stage.rung < PromotionStage.AUTONOMOUS.rung
        else PromotionStage.ASSISTED
    )
    while fresh.stage.rung < inherited.rung:
        # Through `promote`, one rung at a time, rather than assigning the stage
        # behind the guard's back -- and with the truthful promoter and the
        # run's clock. `acknowledging_fixed_values` says what is true of an
        # inherited rung: a fixed-value write skill only reaches ASSISTED
        # because somebody read what it sends, and this version sends the same
        # thing.
        fresh.promote(fresh.stage.next_stage(), at, REPAIR, acknowledging_fixed_values=True)
    return fresh.version


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
            f"{drift.taught.describe()} is being reached by {drift.matched} rather than by the "
            f"{drift.taught.strategy.value} this skill was taught with, and this version does "
            "not say which control that is. Where is it now?"
        ),
        options=("demonstrate the step again", "leave the skill as it is and keep escalating"),
        because=(
            f"{SETTLED} verified runs of {skill_name} v{version.version} step "
            f"{drift.step.index} agree, most recently run {run.id.value}",
        ),
    )


def _note(run: Run, version: SkillVersion, drifts: tuple[Drift, ...]) -> str:
    """Why this version exists, in the words the console shows.

    A skill that quietly rewrites itself is one nobody can trust, so the runs
    that proved the change are named in the provenance rather than only in a log.
    """
    changes = ", ".join(
        f"step {d.step.index} is found by {d.matched} rather than the "
        f"{d.taught.strategy.value} it was taught with"
        for d in drifts
        if d.worked is not None
    )
    return (
        f"repaired from v{version.version} after {SETTLED} verified runs agreed, "
        f"the last of them {run.id.value}: {changes}. Nobody demonstrated this again; "
        "every other step is the one those runs performed."
    )
