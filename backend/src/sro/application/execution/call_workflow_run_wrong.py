"""The operator says a run of a mined job made the wrong record.

The one witness this path has. A run that replays a demonstrated call is
settled by what the warehouse answered and, where the evidence records a read,
by what that read showed -- and neither can see a record that was created
exactly as asked and was not what the person wanted. `verify`'s own note says
so: *that is the one failure the ladder cannot see, and the only witness is the
person whose browser it ran in.*

Not a survey. This is reached by pressing "it's wrong" on the card the run
leaves behind, which is a thing an operator wants to do anyway -- the same
reasoning `call_run_wrong` records for skills, and the reason the answer can be
trusted.

What it costs the job is its autonomy. `effects.forget_effects` empties the
register on a write nobody could show held; this empties it on a write somebody
watched hold and says was wrong, which is the worse of the two. The next runs
of that job ask for a tap again, and it earns its way back from zero.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.call_run_wrong import StillRunning
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.shared.errors import NotFound


class CallWorkflowRunWrong:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, run_id: str, because: str) -> WorkflowRun:
        """Record the report and take the job's autonomy back.

        Scoped to the tenant and to no one narrower, which is where this
        differs from `CallRunWrong` next door. That one checks
        `run.requested_by` because a skill run names the person it ran for. A
        `WorkflowRun` names no person at all -- `started_by` is `form` or
        `offer`, how the run began and not who began it -- so there is nobody
        to compare a principal against, and inventing a comparison against the
        device would refuse the supervisor who is the likeliest reporter.

        A run still going is a 409 rather than a report: there is no result yet
        for anyone to call wrong, and stopping one is `abort` next door.
        """
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
            if run is None:
                # A run of another tenant reads as no such run, which is what
                # every other door on this router answers: a 403 would confirm
                # the id exists somewhere.
                raise NotFound("no such run")
            if run.outcome == "running":
                raise StillRunning("this run is still going; stopping it is a different thing")
            run.wrong_because = because
            await uow.workflow_runs.save(run)
            # Unconditional, and that is the point. `effects.forget_effects`
            # reads the run's own verdicts and would find nothing here: every
            # step said `held`, which is exactly the run this door exists for.
            await uow.workflows.forget_effects(run.workflow_id)
            await uow.commit()
        return run
