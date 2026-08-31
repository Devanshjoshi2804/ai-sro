"""What a skill version has actually done, and whether that earns autonomy.

Promotion to autonomous is the one rung nobody watches, so it is the one rung
that has to be earned by evidence rather than granted by a click. Two things
count, and both are refusals more often than permissions.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation


class Verdict(StrEnum):
    """What a finished run says about the skill that produced it.

    Defined here rather than with execution because it is a fact about a
    *record*: a run either advances a version's case for autonomy, resets it, or
    says nothing. Execution decides which one a given run was.
    """

    CLEAN = "clean"
    """Every step performed at L1, every assertion passed. The only kind of run
    that counts towards autonomy."""

    DEGRADED = "degraded"
    """It worked, but a slower rung had to finish it. Evidence the skill is
    drifting: it resets the counter rather than advancing it."""

    FAILED = "failed"

    WITHHELD = "withheld"
    """A shadow run. It proves the request was buildable and nothing more, so it
    neither advances nor resets anything."""

    UNREACHABLE = "unreachable"
    """It never reached the system it was aiming at, so it says nothing about the
    skill either way.

    A closed laptop, no tab open on the system, a connection that died before a
    response. The trigger already treats this as ordinary -- a browser that
    cannot be reached does not stop a trigger, because it will be open again
    before the next one -- and a run has no better claim to be evidence than the
    trigger that started it. Counted, so the record says the attempt happened;
    counted separately, so nobody reads it as either a success or a fault."""


REQUIRED_CLEAN_RUNS = 10
"""Consecutive clean runs before autonomy is available.

Consecutive, not cumulative: a skill that works nine times in ten is a skill
that will quietly do the wrong thing on a Tuesday, and a total would hide that
behind a good average.
"""

DEMOTE_AFTER_FAILURES = 3
"""Consecutive failures that pull an autonomous skill back to assisted.

Low on purpose. The cost of demoting a healthy skill is that a human confirms
the next few runs; the cost of not demoting a broken one is that it keeps
writing.
"""


@dataclass(frozen=True, slots=True)
class TrackRecord:
    clean_streak: int = 0
    consecutive_failures: int = 0
    clean_runs: int = 0
    degraded_runs: int = 0
    failed_runs: int = 0
    unreachable_runs: int = 0
    """Attempts that never reached the system. Kept in its own column rather
    than folded into the failures or left out: a reviewer asking why a skill has
    four runs and two clean ones deserves the third number instead of having to
    infer that something is missing."""

    last_run_at: datetime | None = None

    failures_before_the_last_run: int = 0
    """What `consecutive_failures` held before the most recent counted run.

    Kept for exactly one reader, `instead_of` below. `consecutive_failures` is
    collapsed to zero by any clean run, so a verdict that is later replaced --
    a run that ended clean and that the operator then said made the wrong
    record -- had already destroyed the number the replacement needs to count
    up from. One integer is the whole of what it takes to put that back, and
    the alternative is a version that made the wrong record every single time
    never reaching three failures in a row because each of its own runs reset
    the count on the way past.

    Not a second track record and not history: it describes the one run that
    can still be revised, which is the run the panel offers "it's wrong" for.
    """

    @property
    def total_runs(self) -> int:
        return self.clean_runs + self.degraded_runs + self.failed_runs + self.unreachable_runs

    def after(self, verdict: Verdict, at: datetime) -> TrackRecord:
        """The record this run leaves behind."""
        counted = self._counted(verdict, at)
        if counted is self:
            # WITHHELD: a shadow run counts nothing, so there is nothing to
            # revise later and nothing to remember about what came before it.
            return self
        return replace(counted, failures_before_the_last_run=self.consecutive_failures)

    def _counted(self, verdict: Verdict, at: datetime) -> TrackRecord:
        if at.tzinfo is None:
            raise InvariantViolation("a run's time must be timezone-aware")

        match verdict:
            case Verdict.CLEAN:
                return replace(
                    self,
                    clean_streak=self.clean_streak + 1,
                    consecutive_failures=0,
                    clean_runs=self.clean_runs + 1,
                    last_run_at=at,
                )
            case Verdict.DEGRADED:
                # Not a failure, and not progress. A run that needed the browser
                # or a model is evidence the recipe no longer fits the system.
                return replace(
                    self,
                    clean_streak=0,
                    consecutive_failures=0,
                    degraded_runs=self.degraded_runs + 1,
                    last_run_at=at,
                )
            case Verdict.FAILED:
                return replace(
                    self,
                    clean_streak=0,
                    consecutive_failures=self.consecutive_failures + 1,
                    failed_runs=self.failed_runs + 1,
                    last_run_at=at,
                )
            case Verdict.UNREACHABLE:
                # Neither a step forward nor a step back. The streak survives it
                # because a browser that was closed is not the skill drifting,
                # and the failure count survives it because three closed laptops
                # in a row would otherwise demote a skill that has never once
                # done anything wrong.
                return replace(
                    self,
                    unreachable_runs=self.unreachable_runs + 1,
                    last_run_at=at,
                )
            case Verdict.WITHHELD:
                return self

    def instead_of(self, already: Verdict, verdict: Verdict, at: datetime) -> TrackRecord:
        """The record after a verdict already counted is replaced by another.

        One run is one run. `CallRunWrong` judges a run `FinishRun` has already
        judged, so counting both left a single attempt with two entries --
        `total_runs` and `clean_runs` overstating permanently, and `earn`
        reading a clean run that, on the operator's own account, never
        happened.

        Three things are put back, and the third is the one that matters.

        The count column of the replaced verdict is decremented before the new
        one is applied, which is exact.

        `consecutive_failures` is rewound to what it held before the replaced
        verdict touched it, from `failures_before_the_last_run`, and only then
        is the new verdict applied on top. Restoring what the replaced verdict
        cleared is precisely this method's job: without it, the sequence that
        actually happens -- a run ends clean, the operator looks at what it
        made and says it is wrong, repeat -- oscillates between zero and one
        forever, because every run's own clean verdict resets the count before
        the operator's answer can raise it. `DEMOTE_AFTER_FAILURES` then never
        fires, and a version that makes the wrong record every single time runs
        assisted indefinitely. That is the backstop ADR 014 rests its whole
        residual-risk argument on, so it has to hold through the ordinary
        sequence and not only through three outright crashes.

        `clean_streak` is not rewound and does not need to be: every revision
        this codebase can make lands on FAILED -- `judge` reads
        `wrong_because` before anything else and `CallRunWrong` is the only
        caller with a verdict to replace -- and FAILED sets the streak to zero
        outright rather than relative to what was there. A revision *to* CLEAN
        would need the same treatment as the failures above; nothing can make
        one, and a second remembered integer for a case that cannot arise is
        a field to keep correct forever in exchange for nothing.

        ponytail: the remembered number describes the most recently counted
        run. Calling a run wrong that is not that one -- two devices running
        the same version, and the older result queried last -- rewinds to the
        wrong base. The panel only ever offers "it's wrong" for the run it just
        watched finish, so nothing reaches that today; the fix if it ever does
        is to remember the number on the `Run` rather than on the record.
        """
        undone = {
            Verdict.CLEAN: "clean_runs",
            Verdict.DEGRADED: "degraded_runs",
            Verdict.FAILED: "failed_runs",
            Verdict.UNREACHABLE: "unreachable_runs",
        }.get(already)
        if undone is None:
            # WITHHELD counted nothing, so there is nothing to take back.
            return self.after(verdict, at)
        # Clamped rather than refused. A run whose first verdict never reached
        # this version -- one finished before the record existed, or against a
        # version since replaced -- is a plausible thing to be handed, and the
        # operator pressing "it's wrong" must not be the person who finds out.
        # Taking nothing back where there is nothing to take back leaves the
        # counts honest either way; raising would only turn a stale row into a
        # dead button.
        counted = max(getattr(self, undone) - 1, 0)
        return replace(
            self,
            **{undone: counted},
            consecutive_failures=self.failures_before_the_last_run,
        ).after(verdict, at)

    @property
    def should_demote(self) -> bool:
        return self.consecutive_failures >= DEMOTE_AFTER_FAILURES


def why_not_autonomous(
    record: TrackRecord,
    *,
    verifiable: bool,
    needs_a_person: bool = False,
    unchecked_writes: str = "no step",
) -> str | None:
    """The reason autonomy is refused, or ``None`` when it is earned.

    A reason rather than a boolean because this is shown to whoever asked, and
    "no" without "because" is how a governance gate becomes a thing people work
    around.
    """
    if not verifiable:
        return (
            f"{unchecked_writes} of this skill cannot be checked, so a run of it proves "
            "only that a request was sent; a skill that cannot be verified may run "
            "assisted indefinitely and never unattended"
        )
    if needs_a_person:
        # Not "not yet" -- not ever. A step with no call behind it is performed
        # as a gesture, `judge` calls any run that performs one degraded, and a
        # degraded run resets the streak. So this version cannot accumulate the
        # ten it would need, and reporting only the count would leave somebody
        # waiting for a number that is never going to move.
        return (
            "a step of this skill can only be performed by clicking, so every run of it "
            "is degraded and the streak below can never reach "
            f"{REQUIRED_CLEAN_RUNS}; it may run assisted with a person pressing the "
            "button, and never unattended"
        )
    if record.clean_streak < REQUIRED_CLEAN_RUNS:
        return f"{record.clean_streak} clean runs in a row, {REQUIRED_CLEAN_RUNS} needed" + (
            " — the streak was reset by a run that needed a slower rung"
            if record.degraded_runs
            else ""
        )
    return None
