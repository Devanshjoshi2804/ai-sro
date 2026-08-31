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

Where the evidence never agrees with itself, a person is asked too, and that is
the third answer. A control reached the taught way on some runs and another way
on others settles nothing, ever: the store goes on recording both, no version is
written, every run pays the escalation again, and nobody is told -- the operator
sees a skill that simply never gets faster. It is still not adopted on a
majority. A locator that only ever matches when the taught one failed has not
proved itself; it has proved the taught one unreliable, which is a different
fact and not one a machine may act on. So the counts are put to somebody who
works there, once, and their answer adopts down the same path evidence does.
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
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.locator import ControlLocator
from sro.domain.skill.plan import UiPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill, SkillStep, SkillVersion
from sro.domain.skill.track_record import REQUIRED_CLEAN_RUNS, TrackRecord

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

Three is also what makes the chain terminate. The store is asked for the newest
three claims about the control; once the repair is adopted the step leads with
the locator that worked, later runs find it where they were taught, and the
claims stop saying it drifted. A drift is adopted once, not once per run.
"""

WINDOW = REQUIRED_CLEAN_RUNS
"""How far back a control is read before calling it contested.

Not a number of its own: it is the streak the drift is denying. ``AUTONOMOUS``
asks for ten clean runs in a row, and a run that fell through its plan to reach
this control is never one of them -- so if inside the last ten claims about a
control the store holds ``SETTLED`` runs saying it moved and ``SETTLED`` saying
it did not, this skill has spent the whole climb unable to start it, and will
go on doing that forever because neither reading will ever outlast the other.

Both sides have to reach ``SETTLED``, which is the same bar and the same
reasoning as adoption: one observation is a slow page, three is a fact, and a
control is only *contested* when there are two facts. Three drifted claims and
one that was not is not a contest -- it is a settled drift with a flake in it,
and the next agreeing run adopts it. That asymmetry is deliberate: asking is
cheap, but a question nobody needed to answer is how a question surface becomes
one nobody reads.
"""


@dataclass(frozen=True, slots=True)
class Drift:
    """One step whose control the store no longer places where it was taught.

    Either because it has settled somewhere else, or because it has not settled
    anywhere -- ``against`` is which.
    """

    step: SkillStep
    plan: UiPlan
    taught: ControlLocator
    matched: str
    agreed: int = SETTLED
    """Verified runs, inside the window, that reached the control by ``matched``."""

    against: int = 0
    """Verified runs inside the window that did not. Zero is a settled drift;
    anything at all here is a contest, and a contest is never adopted on the
    count."""

    answer: str | None = None
    """What somebody said when the contest was put to them, if anybody has."""

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

    @property
    def adopted(self) -> ControlLocator | None:
        """The locator to put in front of this step's plan, if anything says to.

        A settled drift says to. A contested one says so only through a person:
        the same locator, reached through the same repair, so there is one way a
        locator changes and one audit trail rather than two.
        """
        worked = self.worked
        if worked is None:
            return None
        if not self.against:
            return worked
        return worked if self.answer == worked.describe() else None

    @property
    def contest(self) -> str:
        """What the contest is addressed by: the control, not the skill.

        The same button contested across five skills is one question. The store
        is keyed by control already, and so is this."""
        return f"control {self.taught.describe()} is reached two ways"


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
                drift.step.index: _trying_first(drift, adopted)
                for drift in drifts
                if (adopted := drift.adopted) is not None
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
            # Nothing to adopt and nobody has said what to do about it. A
            # contest already answered is not asked again -- `raise_question` is
            # idempotent anyway, and so is this.
            if drift.adopted is None and drift.answer is None:
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
        """Every step of this version the store no longer agrees with."""
        for step in version.steps:
            plan = step.ui_plan
            if plan is None or not plan.locators:
                continue
            taught = plan.locators[0]
            reading = _reading(
                await uow.knowledge.history(
                    ctx.tenant_id,
                    system=system,
                    kind=EntryKind.SCREEN,
                    # The same key `LearnFromRun` writes: the control, not the
                    # skill. Two skills clicking one button are two observations
                    # of where that button is.
                    key=f"control {taught.describe()}",
                    limit=WINDOW,
                )
            )
            if reading is None:
                continue
            matched, agreed, against = reading
            drift = Drift(
                step=step,
                plan=plan,
                taught=taught,
                matched=matched,
                agreed=agreed,
                against=against,
            )
            yield (
                drift
                if not against
                else replace(
                    drift,
                    answer=await _answer(uow, ctx.tenant_id, system=system, key=drift.contest),
                )
            )


async def _answer(uow: UnitOfWork, tenant_id: TenantId, *, system: str, key: str) -> str | None:
    """What somebody decided about a contested control, if anybody has.

    Read through the same port the evidence is read through rather than through
    `AskAbout.settled`, which opens a unit of work of its own -- entering this
    one twice leaves the caller's block without a session. An answer is a claim
    like any other and the history of the question's key is where it lands.
    """
    for entry in await uow.knowledge.history(
        tenant_id, system=system, kind=EntryKind.QUESTION, key=key, limit=SETTLED
    ):
        answer = entry.body.get("answer")
        if isinstance(answer, str):
            return answer
    return None


def _reading(entries: tuple[KnowledgeEntry, ...]) -> tuple[str, int, int] | None:
    """What the store makes of this control: settled elsewhere, contested, or
    nothing worth acting on.

    Settled first, and that ordering is the point. A drift that took a few flaky
    runs to establish itself has both readings in its window and is still a
    drift -- the newest claims agree, so it is adopted and never asked about.
    """
    matched = _settled(entries[:SETTLED])
    if matched is not None:
        return matched, SETTLED, 0
    return _contested(entries)


def _contested(entries: tuple[KnowledgeEntry, ...]) -> tuple[str, int, int] | None:
    """A control the last ``WINDOW`` verified runs cannot agree about.

    ``None`` unless one locator was named by ``SETTLED`` separate runs *and*
    ``SETTLED`` separate runs found the control some other way. Both sides have
    to clear the bar adoption clears: below it, the minority is a slow page and
    the majority is on its way to settling on its own.

    Where two locators both clear it, the more-claimed one is what the question
    leads with -- it is a question, not an adoption, and the counts go with it.
    """
    verified = [entry for entry in entries if entry.evidence.rank >= SUPPORTS_AUTOMATION.rank]
    drifted: dict[str, set[str]] = {}
    for entry in verified:
        if entry.body.get("drifted") is True:
            drifted.setdefault(str(entry.body.get("found_by")), set()).add(entry.source)
    if not drifted:
        return None
    matched, agreed = max(drifted.items(), key=lambda claim: (len(claim[1]), claim[0]))
    against = {entry.source for entry in verified} - agreed
    if len(agreed) < SETTLED or len(against) < SETTLED:
        return None
    return matched, len(agreed), len(against)


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
        promoted_from="",
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
    if drift.against:
        return _contest(drift, run=run, system=system, skill_name=skill_name, version=version)
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


def _contest(
    drift: Drift, *, run: Run, system: str, skill_name: str, version: SkillVersion
) -> Ambiguity:
    """The counts, the cost, and the two things somebody could do about them.

    "Which locator should this use?" is unanswerable on its own -- nobody knows
    what that means about a screen they cannot see. What is answerable is *this
    button is reached one way on seven runs in ten and another way on the other
    three, and the skill cannot get faster while that is true*: somebody who
    works in that warehouse knows whether the screen has two of these, or one
    that is slow to render, or one that moved during a release.
    """
    worked = drift.worked
    total = drift.agreed + drift.against
    return Ambiguity(
        system=system,
        key=drift.contest,
        question=(
            f"{drift.taught.describe()} is reached by {drift.matched} on some runs and by the "
            f"{drift.taught.strategy.value} it was taught with on others. Neither is rare enough "
            "to be a slow page, so nothing here will ever settle on its own. Which should this "
            "skill lead with?"
        ),
        options=(
            # Answered with exactly what the plan calls the locator, because
            # that answer is what adopts it -- through the same repair a settled
            # drift takes, so there is one way a locator changes.
            worked.describe() if worked is not None else "demonstrate the step again",
            "leave it as it is and keep escalating",
        ),
        because=(
            f"{drift.agreed} of the last {total} verified runs reached it by {drift.matched}; "
            f"{drift.against} found it by the {drift.taught.strategy.value} it was taught with",
            f"{skill_name} v{version.version} step {drift.step.index} falls through its plan on "
            f"{drift.agreed} runs in {total} and a run that does is never clean, so the "
            f"{REQUIRED_CLEAN_RUNS} clean runs unattended running needs never start -- and no "
            "amount of running fixes that, because the evidence contradicts itself every time",
            f"most recently run {run.id.value}",
        ),
    )


def _note(run: Run, version: SkillVersion, drifts: tuple[Drift, ...]) -> str:
    """Why this version exists, in the words the console shows.

    A skill that quietly rewrites itself is one nobody can trust, so the runs
    that proved the change are named in the provenance rather than only in a log.
    """
    adopted = [d for d in drifts if d.adopted is not None]
    changes = ", ".join(
        f"step {d.step.index} is found by {d.matched} rather than the "
        f"{d.taught.strategy.value} it was taught with"
        + (f" ({d.agreed} runs to {d.against}, answered by hand)" if d.against else "")
        for d in adopted
    )
    proof = (
        f"after {SETTLED} verified runs agreed, the last of them {run.id.value}"
        if all(not d.against for d in adopted)
        else f"after somebody settled what the runs could not, most recently {run.id.value}"
    )
    return (
        f"repaired from v{version.version} {proof}: {changes}. "
        "Nobody demonstrated this again; every other step is the one those runs performed."
    )
