from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.run import Run, RunStatus
from sro.domain.execution.verdict import judge
from sro.domain.skill.track_record import Verdict
from sro.domain.skill.workflow import Workflow

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
    clean: int
    degraded: int
    failed: int
    withheld: int
    unreachable: int

    writes_sent: int


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
            workflows = await uow.workflows.known(ctx.tenant_id)
            runs = await uow.runs.since(ctx.tenant_id, since=since)

        lines = tuple(_line(workflow) for workflow in workflows)
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


def _doing(runs: Sequence[Run]) -> Doing:
    verdicts = [judge(run) for run in runs if run.status is not RunStatus.RUNNING]
    return Doing(
        runs=len(runs),
        clean=verdicts.count(Verdict.CLEAN),
        degraded=verdicts.count(Verdict.DEGRADED),
        failed=verdicts.count(Verdict.FAILED),
        withheld=verdicts.count(Verdict.WITHHELD),
        unreachable=verdicts.count(Verdict.UNREACHABLE),
        writes_sent=sum(run.writes_sent for run in runs),
    )


def _line(workflow: Workflow) -> TaskLine:
    return TaskLine(
        id=workflow.id,
        title=workflow.title,
        host=", ".join(workflow.systems),
        kind=kind_of(workflow.title),
        steps=len(workflow.steps),
    )


def _by_kind(lines: Sequence[TaskLine]) -> dict[str, int]:
    kinds: dict[str, int] = {}
    for line in lines:
        kinds[line.kind] = kinds.get(line.kind, 0) + 1
    return dict(sorted(kinds.items(), key=lambda pair: pair[1], reverse=True))


def kind_of(title: str) -> str:
    first = title.split(" ", 1)[0]
    return first if first in ("Create", "Update", "Read", "Remove") else "other"
