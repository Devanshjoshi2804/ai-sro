"""Everything a person would want to see after the fact, since a time.

The runs with each step's verdict and what was sent, when a person approved a
write, every offer's fate, which browsers could act and until when, and what
the chat door cost. Four reads plan 2 gave the repositories, one tenant, one
bound, each list newest first.

Nothing here computes. The summary beside it derives numbers; this hands back
rows somebody can open, because an audit that summarised would be answering a
question other than the one it was asked. The only work it does is turn one
instant into the one string all four reads compare against -- which is the
whole of what a "since" is, and the reason it is a use case rather than four
calls a route makes in a row.

Ported from the rig's ``GET /v1/audit``. Two of that route's rules are
deliberately not here: its ``limit`` is a page size and belongs to whoever
serves a page, and the repository reads plan 2 landed take no limit; and its
device select had no tenant filter at all, so one tenant's audit listed every
tenant's browsers -- a leak rather than a rule, already fixed in
``SqlDeviceRepository.since`` and not travelling here.

Nor does its ``since: str = ""``, which meant "everything ever". ``since`` is a
``datetime`` and required: an audit of all time is a table scan nobody asked
for, and a caller that wants one can say when the deployment started.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.chat.reading import ChatReading
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.device import AgentDevice
from sro.domain.skill.offers import Offer


@dataclass(frozen=True, slots=True)
class AuditedRun:
    run: WorkflowRun
    approvals: tuple[tuple[int, str, str | None], ...]
    """(step ord, when, which browser) for each write a person let out.

    Beside the run rather than folded into its steps: a ``RunStep`` is what the
    runner writes and an approval is what a person did, and a record that
    carried both could be saved back with somebody's approval in it.
    """


@dataclass(frozen=True, slots=True)
class Audit:
    since: str
    """The bound the four reads actually used, normalised -- not the argument.

    Handed back because a reader has to be able to tell which instant they got:
    a caller that passed a naive time is told, in UTC, what that was taken to
    mean.
    """

    runs: tuple[AuditedRun, ...]
    offers: tuple[Offer, ...]
    devices: tuple[AgentDevice, ...]
    chats: tuple[ChatReading, ...]


class ReadAudit:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, since: datetime) -> Audit:
        bound = _bound(since)
        async with self._uow as uow:
            runs = await uow.workflow_runs.since(ctx.tenant_id, since=bound)
            # ``approvals`` is tenant-blind, and is only safe asked this way:
            # every run id here came out of a tenant-scoped read a line above,
            # so nothing crosses that boundary by asking with an id a caller
            # supplied.
            audited = [
                AuditedRun(run=run, approvals=await uow.workflow_runs.approvals(run.id))
                for run in runs
            ]
            offers = await uow.offers.since(ctx.tenant_id, since=bound)
            devices = await uow.devices.since(ctx.tenant_id, since=bound)
            chats = await uow.chats.since(ctx.tenant_id, since=bound)
        return Audit(
            since=bound,
            runs=tuple(audited),
            offers=offers,
            devices=devices,
            chats=chats,
        )


def _bound(since: datetime) -> str:
    """One instant, in UTC, as all four reads compare it.

    A naive ``since`` is read as UTC and never as the server's local time --
    ``sro.infrastructure.db.codec.when``'s rule on the other edge, and the
    rig's on this one. A bound quietly shifted by the host's offset does not
    fail; it returns an audit that starts hours from where it was asked to,
    and looks exactly like one that does not.
    """
    return (since if since.tzinfo else since.replace(tzinfo=UTC)).astimezone(UTC).isoformat()
