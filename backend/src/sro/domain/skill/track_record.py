from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation


class Verdict(StrEnum):
    CLEAN = "clean"

    DEGRADED = "degraded"

    FAILED = "failed"

    WITHHELD = "withheld"

    UNREACHABLE = "unreachable"


REQUIRED_CLEAN_RUNS = 10

DEMOTE_AFTER_FAILURES = 3


@dataclass(frozen=True, slots=True)
class TrackRecord:
    clean_streak: int = 0
    consecutive_failures: int = 0
    clean_runs: int = 0
    degraded_runs: int = 0
    failed_runs: int = 0
    unreachable_runs: int = 0

    last_run_at: datetime | None = None

    failures_before_the_last_run: int = 0

    @property
    def total_runs(self) -> int:
        return self.clean_runs + self.degraded_runs + self.failed_runs + self.unreachable_runs

    def after(self, verdict: Verdict, at: datetime) -> TrackRecord:
        counted = self._counted(verdict, at)
        if counted is self:
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
                return replace(
                    self,
                    unreachable_runs=self.unreachable_runs + 1,
                    last_run_at=at,
                )
            case Verdict.WITHHELD:
                return self

    def instead_of(self, already: Verdict, verdict: Verdict, at: datetime) -> TrackRecord:
        undone = {
            Verdict.CLEAN: "clean_runs",
            Verdict.DEGRADED: "degraded_runs",
            Verdict.FAILED: "failed_runs",
            Verdict.UNREACHABLE: "unreachable_runs",
        }.get(already)
        if undone is None:
            return self.after(verdict, at)
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
    if not verifiable:
        return (
            f"{unchecked_writes} of this skill cannot be checked, so a run of it proves "
            "only that a request was sent; a skill that cannot be verified may run "
            "assisted indefinitely and never unattended"
        )
    if needs_a_person:
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
