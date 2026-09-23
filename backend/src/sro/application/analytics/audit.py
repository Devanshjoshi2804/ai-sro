from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.chat.reading import ChatReading
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.attempts import Attempt
from sro.domain.observation.device import AgentDevice
from sro.domain.skill.offers import Offer

K_ATTEMPTS = 500


@dataclass(frozen=True, slots=True)
class AuditedRun:
    run: WorkflowRun
    approvals: tuple[tuple[int, str, str | None], ...]


@dataclass(frozen=True, slots=True)
class Audit:
    since: str

    runs: tuple[AuditedRun, ...]
    offers: tuple[Offer, ...]
    devices: tuple[AgentDevice, ...]
    chats: tuple[ChatReading, ...]

    attempts: tuple[Attempt, ...] = ()


class ReadAudit:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, since: datetime) -> Audit:
        bound = _bound(since)
        async with self._uow as uow:
            runs = await uow.workflow_runs.since(ctx.tenant_id, since=bound)
            audited = [
                AuditedRun(run=run, approvals=await uow.workflow_runs.approvals(run.id))
                for run in runs
            ]
            offers = await uow.offers.since(ctx.tenant_id, since=bound)
            devices = await uow.devices.since(ctx.tenant_id, since=bound)
            chats = await uow.chats.since(ctx.tenant_id, since=bound)
            attempts = await uow.attempts.since(ctx.tenant_id, since=since, limit=K_ATTEMPTS)
        return Audit(
            since=bound,
            runs=tuple(audited),
            offers=offers,
            devices=devices,
            chats=chats,
            attempts=attempts,
        )


def _bound(since: datetime) -> str:
    return (since if since.tzinfo else since.replace(tzinfo=UTC)).astimezone(UTC).isoformat()
