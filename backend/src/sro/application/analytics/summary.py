from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.skill.workflow import Noticed

MOST = 10


@dataclass(frozen=True, slots=True)
class Watching:
    devices: int
    batches: int
    events: int
    hours: float


@dataclass(frozen=True, slots=True)
class Noticing:
    tasks: int
    by_kind: dict[str, int]


@dataclass(frozen=True, slots=True)
class Doing:
    runs: int
    rehearsed: int
    outcomes: dict[str, int]


@dataclass(frozen=True, slots=True)
class TaskLine:
    id: str
    title: str
    host: str
    kind: str
    steps: int


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
            noticed = await uow.workflows.noticed_since(ctx.tenant_id, since=since)
            runs = await uow.workflow_runs.since(ctx.tenant_id, since=since.isoformat())

        lines = tuple(_line(job) for job in noticed)
        return Summary(
            since=since,
            watching=Watching(
                devices=len(devices),
                batches=len(batches),
                events=sum(batch.event_count for batch in batches),
                hours=round(sum(batch.spans_seconds for batch in batches) / 3600, 1),
            ),
            noticing=Noticing(tasks=len(lines), by_kind=_by_kind(lines)),
            doing=_doing(runs),
            tasks=lines[:MOST],
        )


def _doing(runs: Sequence[WorkflowRun]) -> Doing:
    outcomes: dict[str, int] = {}
    for run in runs:
        outcomes[run.outcome] = outcomes.get(run.outcome, 0) + 1
    return Doing(
        runs=len(runs),
        rehearsed=sum(1 for run in runs if run.outcome == "held" and not run.live),
        outcomes=dict(sorted(outcomes.items(), key=lambda pair: pair[1], reverse=True)),
    )


def _line(job: Noticed) -> TaskLine:
    return TaskLine(
        id=job.id,
        title=job.title,
        host=", ".join(job.systems),
        kind=kind_of(job.title),
        steps=job.steps,
    )


def _by_kind(lines: Sequence[TaskLine]) -> dict[str, int]:
    kinds: dict[str, int] = {}
    for line in lines:
        kinds[line.kind] = kinds.get(line.kind, 0) + 1
    return dict(sorted(kinds.items(), key=lambda pair: pair[1], reverse=True))


def kind_of(title: str) -> str:
    first = title.split(" ", 1)[0]
    return first if first in ("Create", "Update", "Read", "Remove") else "other"
