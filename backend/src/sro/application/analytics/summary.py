"""What the system has watched, noticed and done.

Every number here is derived from rows somebody can open. Nothing is a counter
kept alongside the truth and updated by hand -- a metric that can drift from what
happened is worse than no metric, because it is believed.

The run outcomes are judged with ``judge``, the same function that classified
each run when it finished. A screen that scored runs its own way would sooner or
later disagree with the promotion ladder, and then two things in the same
building would be saying different words about the same afternoon.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.run import Run, RunStatus
from sro.domain.execution.verdict import judge
from sro.domain.observation.candidate import CandidateStatus, TaskCandidate
from sro.domain.skill.track_record import Verdict

MOST = 10
"""How many tasks the summary names. A list nobody scrolls is a list nobody
reads; the rest are on the candidates screen."""


@dataclass(frozen=True, slots=True)
class Watching:
    devices: int
    batches: int
    events: int
    hours: float
    """Hours of work observed. The span of the batches, not their number: an
    extension that uploads every minute would otherwise look like more work."""


@dataclass(frozen=True, slots=True)
class Noticing:
    tasks: int
    worth_offering: int
    taught: int
    dismissed: int
    by_kind: dict[str, int]
    """Create, Update, Read, Remove -- taken from the calls each task makes, not
    from anything a person filled in."""


@dataclass(frozen=True, slots=True)
class Doing:
    runs: int
    clean: int
    degraded: int
    failed: int
    withheld: int
    unreachable: int
    """Runs that never reached the system they were aiming at. Its own number
    because it is neither a success nor a fault, and folding it into either
    would make a week of closed laptops read as a week of a broken skill."""

    writes_sent: int
    minutes_saved: float


@dataclass(frozen=True, slots=True)
class TaskLine:
    # Two candidates can carry the same host and the same title -- mining groups
    # by signature, and two signatures describe themselves the same way. Without
    # this the console keyed rows on host+title, React warned that it could drop
    # one of them, and a reviewer had no way to tell the pair apart.
    id: str
    title: str
    host: str
    kind: str
    status: str
    times_seen: int
    median_seconds: float
    minutes_spent: float
    skill_id: str | None
    runs: int
    minutes_saved: float


@dataclass(frozen=True, slots=True)
class Summary:
    since: datetime
    watching: Watching
    noticing: Noticing
    doing: Doing
    tasks: tuple[TaskLine, ...]


class ReadSummary:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, since: datetime) -> Summary:
        async with self._uow as uow:
            devices = await uow.devices.list_for_tenant(ctx.tenant_id)
            batches = await uow.observations.between(ctx.tenant_id, since=since)
            candidates = await uow.candidates.list_for_tenant(ctx.tenant_id)
            runs = await uow.runs.since(ctx.tenant_id, since=since)

        # list_for_tenant has no window of its own -- it is every candidate this
        # tenant has ever had, dismissed or not. Without this, the day-range
        # control on the screen would change everything except what it looks
        # most like it should change.
        candidates = tuple(
            candidate
            for candidate in candidates
            if candidate.last_seen is None or candidate.last_seen >= since
        )

        by_skill = _runs_by_skill(runs)
        lines = tuple(
            sorted(
                (_line(candidate, by_skill) for candidate in candidates),
                key=lambda line: (line.minutes_saved, line.minutes_spent),
                reverse=True,
            )
        )

        return Summary(
            since=since,
            watching=Watching(
                devices=len(devices),
                batches=len(batches),
                events=sum(batch.event_count for batch in batches),
                hours=round(sum(batch.spans_seconds for batch in batches) / 3600, 1),
            ),
            noticing=Noticing(
                tasks=len(candidates),
                worth_offering=sum(1 for one in candidates if one.worth_offering),
                taught=sum(1 for one in candidates if one.status is CandidateStatus.TAUGHT),
                dismissed=sum(1 for one in candidates if one.status is CandidateStatus.DISMISSED),
                by_kind=_by_kind(candidates),
            ),
            doing=_doing(runs, lines),
            tasks=lines[:MOST],
        )


def _doing(runs: Sequence[Run], lines: Sequence[TaskLine]) -> Doing:
    verdicts = [judge(run) for run in runs if run.status is not RunStatus.RUNNING]
    return Doing(
        runs=len(runs),
        clean=verdicts.count(Verdict.CLEAN),
        degraded=verdicts.count(Verdict.DEGRADED),
        failed=verdicts.count(Verdict.FAILED),
        withheld=verdicts.count(Verdict.WITHHELD),
        unreachable=verdicts.count(Verdict.UNREACHABLE),
        writes_sent=sum(run.writes_sent for run in runs),
        minutes_saved=round(sum(line.minutes_saved for line in lines), 1),
    )


def _line(candidate: TaskCandidate, by_skill: dict[str, int]) -> TaskLine:
    runs = by_skill.get(candidate.skill_id.value, 0) if candidate.skill_id else 0
    # What the person would have spent doing it by hand, times the number of
    # times the system did it instead. Stated that way on the screen too: it is
    # an estimate built from one measurement, not a measurement.
    saved = runs * candidate.median_duration_ms / 60_000
    return TaskLine(
        id=candidate.id.value,
        title=candidate.title,
        host=candidate.host,
        kind=kind_of(candidate.title),
        status=candidate.status.value,
        times_seen=candidate.times_seen,
        median_seconds=round(candidate.median_duration_ms / 1000, 1),
        minutes_spent=round(candidate.minutes_so_far, 1),
        skill_id=candidate.skill_id.value if candidate.skill_id else None,
        runs=runs,
        minutes_saved=round(saved, 1),
    )


def _runs_by_skill(runs: Sequence[Run]) -> dict[str, int]:
    """Only the ones that worked. A failed run saved nobody anything, and
    counting it would make a broken skill look like its best week."""
    counted: dict[str, int] = {}
    for run in runs:
        if run.status is RunStatus.SUCCEEDED and judge(run) is not Verdict.WITHHELD:
            counted[run.skill_id.value] = counted.get(run.skill_id.value, 0) + 1
    return counted


def _by_kind(candidates: Sequence[TaskCandidate]) -> dict[str, int]:
    kinds: dict[str, int] = {}
    for candidate in candidates:
        kind = kind_of(candidate.title)
        kinds[kind] = kinds.get(kind, 0) + 1
    return dict(sorted(kinds.items(), key=lambda pair: pair[1], reverse=True))


def kind_of(title: str) -> str:
    """The verb a mined title starts with. A renamed candidate falls back to
    "other" rather than being guessed at."""
    first = title.split(" ", 1)[0]
    return first if first in ("Create", "Update", "Read", "Remove") else "other"
