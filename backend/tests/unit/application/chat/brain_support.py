"""A world for the brain's tools: the real use cases over the fakes.

Jobs are stored as mining stores them (a workflow row and the gestures its
steps cite), and the mail look is the real `FromTheMail` over a scripted
mailbox, as the from-the-mail tests build it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.from_the_mail import FromTheMail
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.execution.workflow_runs import ListWorkflowRuns
from sro.domain.chat.asking import NEEDS
from sro.domain.chat.thread import Speaker
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.shared.identifiers import PrincipalId
from tests import factories as f
from tests.unit.application.rig.test_from_the_mail import (
    JOB,
    _found,
    _held,
    _look,
    _mail,
    _Mailbox,
    _Reads,
)
from tests.unit.fakes import FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("devansh"))
THEIRS = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("someone-else"))


@dataclass
class World:
    uow: FakeUnitOfWork
    look: FromTheMail
    runs: ListWorkflowRuns
    threads: ReadThreads
    clock: FakeClock

    async def ran(
        self,
        outcome: str,
        values: dict[str, str],
        *,
        run_id: str = "run_1",
        by: RequestContext = CTX,
        steps: tuple[RunStep, ...] = (),
        mail: dict[str, str] | None = None,
        tenant: str = f.TENANT.value,
    ) -> WorkflowRun:
        run = WorkflowRun(
            id=run_id,
            tenant=tenant,
            workflow_id=JOB,
            device_id="",
            values=values,
            started_by=by.principal_id.value,
            live=False,
            allow_focus=False,
            started_at=datetime(2026, 9, 30, tzinfo=UTC).isoformat(),
            outcome=outcome,
            steps=list(steps),
            mail=mail,
        )
        await self.uow.workflow_runs.save(run)
        return run

    async def asked(self, run: WorkflowRun, text: str) -> None:
        """The question a run put to its operator, in the run's own ask chat."""
        await SayWhatHappened(self.uow, self.clock, FakeIdFactory()).execute(
            CTX,
            for_operator=PrincipalId(run.started_by),
            text=text,
            speaker=Speaker.ASSISTANT,
            decision={"kind": NEEDS, "from_run": run.id, "workflow_id": run.workflow_id},
            about=(run.mail or {}).get("thread") or run.id,
        )


async def world_with_job(*mail: str) -> World:
    """The one mined job, and a mailbox holding these mails (none of which
    asks for any job the model reads)."""
    uow = await _held()
    ids = [f"m-{n}" for n, _ in enumerate(mail, 1)]
    box = _Mailbox(
        search=_found(*ids), **{one: _mail(said) for one, said in zip(ids, mail, strict=True)}
    )
    return World(
        uow, _look(uow, box, _Reads()), ListWorkflowRuns(uow), ReadThreads(uow), FakeClock()
    )


def a_failed_step(reason: str) -> RunStep:
    return replace(RunStep(order=0, says="save", verdict="failed"), reason=reason)
