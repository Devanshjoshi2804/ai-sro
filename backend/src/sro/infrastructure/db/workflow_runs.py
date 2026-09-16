"""Runs of a mined workflow on Postgres: their steps, and the approvals on them.

The rules here are the rig's -- ``rig/runs.py`` plus the approval insert and
the awaiting query in ``rig/api.py`` -- and they were SQLite there. What had to
be translated rather than copied is marked where it happens:

* ``INSERT OR REPLACE`` on a run and ``INSERT OR IGNORE`` on an approval become
  ``ON CONFLICT DO UPDATE`` and ``ON CONFLICT DO NOTHING`` on a named conflict
  target. SQLite's forms swallow *every* constraint; naming the target means a
  different constraint failing is still an error rather than a silent no-op.
  On the approval it also buys the answer: ``RETURNING`` says whether this tap
  was the one that authorised the step, where SQLite gave a rowcount.
* The rig kept every clock as text. ``started_at`` and ``finished_at`` are
  ``timestamptz`` here because both indexes order on ``started_at`` and an
  offset-less string sorts beside an offset-bearing one with neither wrong. The
  records still carry ISO strings, so this converts on both edges.
* ``fail_orphans`` sweeps every tenant, which is not an oversight: it runs once
  at startup with nobody making the request, and a run left ``running`` in one
  tenant goes on 409-ing its browser however healthy the others are.

The row-to-record mapping lives here rather than in ``mappers.py``: a
repository's mapping belongs with the repository, and these three shapes are
read by nothing else.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sro.application.ports.repositories import WorkflowRunRepository
from sro.domain.execution.workflow_run import RunStep, WorkflowRun, already_running
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.infrastructure.db.codec import when
from sro.infrastructure.db.models import ApprovalRow, WorkflowRunRow, WorkflowRunStepRow


def _run_values(run: WorkflowRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "tenant_id": run.tenant,
        "workflow_id": run.workflow_id,
        "device_id": run.device_id,
        "values": dict(run.values),
        "started_by": run.started_by,
        "live": run.live,
        "allow_focus": run.allow_focus,
        "started_at": when(run.started_at),
        "finished_at": None if run.finished_at is None else when(run.finished_at),
        "outcome": run.outcome,
        "from_step": run.from_step,
        "items": [dict(item) for item in run.items],
        "withheld": list(run.withheld),
        "in_tokens": run.in_tokens,
        "out_tokens": run.out_tokens,
        "thought_tokens": run.thought_tokens,
        "cost_usd": run.cost_usd,
        "wrong_because": run.wrong_because,
        "gathered": {k: dict(v) for k, v in run.gathered.items()},
        "unpriced": run.unpriced,
    }


def _step_values(run_id: str, step: RunStep) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "ord": step.order,
        "says": step.says,
        "planned_by": step.planned_by,
        "sent": step.sent,
        "result": step.result,
        "verdict": step.verdict,
        "verdict_by": step.verdict_by,
        "reason": step.reason,
        "matched_by": step.matched_by,
        "stale": step.stale,
        "before_url": step.before_url,
        "after_url": step.after_url,
        "in_tokens": step.in_tokens,
        "out_tokens": step.out_tokens,
        "thought_tokens": step.thought_tokens,
        "cost_usd": step.cost_usd,
        "notes": list(step.notes),
        "unpriced": step.unpriced,
        "of_step": step.of_step,
        "item": step.item,
        "made": dict(step.made),
    }


def _row_to_step(row: WorkflowRunStepRow) -> RunStep:
    return RunStep(
        order=row.ord,
        says=row.says,
        verdict=row.verdict,
        verdict_by=row.verdict_by,
        reason=row.reason,
        planned_by=row.planned_by,
        sent=row.sent,
        result=row.result,
        matched_by=row.matched_by,
        stale=row.stale,
        before_url=row.before_url,
        after_url=row.after_url,
        in_tokens=row.in_tokens,
        out_tokens=row.out_tokens,
        thought_tokens=row.thought_tokens,
        cost_usd=row.cost_usd,
        unpriced=row.unpriced,
        notes=[note for note in (row.notes or []) if isinstance(note, str)],
        of_step=row.of_step,
        item=row.item,
        made=dict(row.made or {}),
    )


def _row_to_run(row: WorkflowRunRow, steps: list[RunStep]) -> WorkflowRun:
    return WorkflowRun(
        id=row.id,
        tenant=row.tenant_id,
        workflow_id=row.workflow_id,
        device_id=row.device_id,
        values=dict(row.values_),
        started_by=row.started_by,
        live=row.live,
        allow_focus=row.allow_focus,
        started_at=row.started_at.isoformat(),
        finished_at=None if row.finished_at is None else row.finished_at.isoformat(),
        outcome=row.outcome,
        wrong_because=row.wrong_because,
        gathered={
            str(k): {str(a): str(b) for a, b in v.items()}
            for k, v in (row.gathered or {}).items()
            if isinstance(v, dict)
        },
        from_step=row.from_step,
        items=[dict(item) for item in (row.items or [])],
        steps=steps,
        withheld=list(row.withheld),
        in_tokens=row.in_tokens,
        out_tokens=row.out_tokens,
        thought_tokens=row.thought_tokens,
        cost_usd=row.cost_usd,
        unpriced=row.unpriced,
    )


_ONE_RUNNING = "uq_workflow_runs_one_running_per_device"
"""The one constraint on `workflow_runs` whose violation this module has a
sentence for. Matched as a substring of the driver's own message: asyncpg and
psycopg both name the index there, and `orig.diag.constraint_name` is spelled
differently on each."""


class SqlWorkflowRunRepository(WorkflowRunRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, run: WorkflowRun) -> None:
        statement = pg_insert(WorkflowRunRow).values(**_run_values(run))
        try:
            await self._session.execute(
                statement.on_conflict_do_update(
                    # The id, and only the id. A second running run for a
                    # browser that already has one violates
                    # `uq_workflow_runs_one_running_per_device`, which is NOT
                    # this conflict target, so it raises rather than quietly
                    # updating somebody else's row -- which is the whole point
                    # of naming the target instead of swallowing every
                    # constraint the way SQLite's INSERT OR REPLACE did.
                    index_elements=["id"],
                    # Every column but the key takes the new value, which is
                    # what INSERT OR REPLACE did: a run is written whole after
                    # every step, so the later write supersedes the earlier one.
                    set_={
                        column.name: statement.excluded[column.name]
                        for column in WorkflowRunRow.__table__.columns
                        if column.name != "id"
                    },
                )
            )
        except IntegrityError as clash:
            if _ONE_RUNNING not in str(getattr(clash, "orig", clash)):
                # Some OTHER constraint. Every integrity violation used to be
                # reported as "that browser is already running a run this press
                # cannot see" -- a sentence about a different problem, naming a
                # run that would be `None` because there isn't one, with the
                # caller's transaction already rolled back underneath it so the
                # real cause could not be recovered from the response. There is
                # no second constraint a legal save can violate today, which is
                # exactly why nobody would find this the day one is added.
                raise
            # One browser, one hand -- enforced here because the caller's own
            # `in_flight` read cannot enforce it: between that read and this
            # there are awaits, and two presses on one event loop both read
            # free. The session is finished either way, so it is rolled back
            # before the sentence is composed, which is also what makes the
            # read below possible: the winner's row is visible once this
            # transaction is gone.
            await self._session.rollback()
            busy = await self.in_flight(TenantId(run.tenant), DeviceId(run.device_id))
            raise Conflict(already_running(run.device_id, busy)) from clash
        # Deleted and reinserted rather than upserted one by one. A step
        # removed from the record has to leave the store with it, and an
        # upsert would leave it behind -- and this is the rule the second save
        # of a run depends on to not double its first step.
        await self._session.execute(
            delete(WorkflowRunStepRow).where(WorkflowRunStepRow.run_id == run.id)
        )
        if run.steps:
            await self._session.execute(
                pg_insert(WorkflowRunStepRow).values(
                    [_step_values(run.id, step) for step in run.steps]
                )
            )

    async def get(self, tenant_id: TenantId, run_id: str) -> WorkflowRun | None:
        query = self._rows().where(
            WorkflowRunRow.tenant_id == tenant_id.value, WorkflowRunRow.id == run_id
        )
        rows = (await self._session.execute(query)).scalars().all()
        found = await self._with_steps(rows)
        return found[0] if found else None

    async def for_workflow(self, tenant_id: TenantId, workflow_id: str) -> tuple[WorkflowRun, ...]:
        query = self._rows().where(
            WorkflowRunRow.tenant_id == tenant_id.value,
            WorkflowRunRow.workflow_id == workflow_id,
        )
        rows = (
            await self._session.execute(
                # The id breaks a tie the rig never had to. Two runs of one
                # workflow routinely start in the same instant -- one form
                # submits them -- and `started_at` alone leaves Postgres free to
                # return them in heap order, which is an order that changes
                # between reads. `proofs` has always broken the tie this way.
                query.order_by(WorkflowRunRow.started_at, WorkflowRunRow.id)
            )
        ).scalars()
        return await self._with_steps(rows.all())

    async def recent(
        self,
        tenant_id: TenantId,
        *,
        limit: int,
        workflow_id: str | None = None,
        ids: frozenset[str] | None = None,
    ) -> tuple[WorkflowRun, ...]:
        # The rig's list query (`api.py:1152`), filters and all: tenant, then
        # the job if one was named, then the named set `awaiting=true` narrows
        # to -- and the cap last, after every predicate, because a cap applied
        # before them answers "nothing is waiting" out of a busy tenant.
        query = self._rows().where(WorkflowRunRow.tenant_id == tenant_id.value)
        if workflow_id is not None:
            query = query.where(WorkflowRunRow.workflow_id == workflow_id)
        if ids is not None:
            # An empty set is not "no filter": it is "nothing matches", and
            # `in_` of nothing is exactly that.
            query = query.where(WorkflowRunRow.id.in_(sorted(ids)))
        rows = (
            await self._session.execute(
                # `since`'s order, and for `for_workflow`'s reason: reversed,
                # id and all, so a page boundary falls in the same place twice.
                query.order_by(WorkflowRunRow.started_at.desc(), WorkflowRunRow.id.desc()).limit(
                    limit
                )
            )
        ).scalars()
        return await self._with_steps(rows.all())

    async def failures(self, tenant_id: TenantId) -> Mapping[str, int]:
        # One count for the tenant, beside `tallies` and for the same reason it
        # is batched. `stopped` and `aborted` are deliberately not here: a run
        # that stopped to ask is the job asking, and one a person aborted is a
        # person changing their mind.
        query = (
            select(WorkflowRunRow.workflow_id, func.count())
            .where(
                WorkflowRunRow.tenant_id == tenant_id.value,
                WorkflowRunRow.outcome.in_(("failed", "refused")),
            )
            .group_by(WorkflowRunRow.workflow_id)
        )
        rows = (await self._session.execute(query)).all()
        return {workflow_id: int(count) for workflow_id, count in rows}

    async def tallies(self, tenant_id: TenantId) -> Mapping[str, tuple[int, int]]:
        # The rig's two counts off the runs index, batched: it asked
        # ``COUNT(*), SUM(outcome = 'held')`` per workflow, and this asks the
        # tenant once. ``count(*) FILTER`` rather than SQLite's ``SUM`` of a
        # boolean, which has no meaning in Postgres -- and it counts rows, so
        # a tenant with no held runs gets 0 where the SUM would have given
        # NULL. No ``ORDER BY``: the answer is a mapping and the caller looks
        # each workflow up by id.
        query = (
            select(
                WorkflowRunRow.workflow_id,
                func.count(),
                func.count().filter(WorkflowRunRow.outcome == "held"),
            )
            .where(WorkflowRunRow.tenant_id == tenant_id.value)
            .group_by(WorkflowRunRow.workflow_id)
        )
        rows = (await self._session.execute(query)).all()
        return {workflow_id: (int(ran), int(held)) for workflow_id, ran, held in rows}

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[WorkflowRun, ...]:
        # Newest first, unlike ``for_workflow``: this is the audit's order, and
        # a person reading what happened reads back from now. No limit --
        # paging belongs to the route, which is where the rig's was.
        query = self._rows().where(
            WorkflowRunRow.tenant_id == tenant_id.value,
            WorkflowRunRow.started_at >= when(since),
        )
        rows = (
            await self._session.execute(
                # Reversed, id and all: the audit's order has to be total for
                # the same reason `for_workflow`'s does, and every sibling read
                # here breaks its tie the same way -- `offers.since` on
                # `seq DESC`, `known` on the id.
                query.order_by(WorkflowRunRow.started_at.desc(), WorkflowRunRow.id.desc())
            )
        ).scalars()
        return await self._with_steps(rows.all())

    async def in_flight(self, tenant_id: TenantId, device_id: DeviceId) -> str | None:
        # A read the caller acts on, and no longer the only thing standing
        # between two presses and one browser: migration 0043 added the UNIQUE
        # partial index on (tenant_id, device_id) WHERE outcome = 'running'
        # that the note here used to ask a future worker for.
        #
        # This stays because it is the answer a person can act on -- it names
        # the run already driving, where the index can only refuse. The index
        # is the backstop for the race this read cannot see: there are two
        # awaits between it and the commit, and two gathered presses against
        # real Postgres both claimed the browser before it existed.
        busy: str | None = await self._session.scalar(
            select(WorkflowRunRow.id)
            .where(
                WorkflowRunRow.tenant_id == tenant_id.value,
                WorkflowRunRow.device_id == device_id.value,
                WorkflowRunRow.outcome == "running",
            )
            # Total, so that a device somehow driving two runs at one instant
            # names the same one of them on every read rather than whichever
            # Postgres happens to hand back first.
            #
            # 0043 makes that state unreachable through this schema, so the
            # ordering is now defensive rather than load-bearing, and the test
            # that planted two running rows to prove the tie-break went with it.
            # Kept anyway: a hand-typed INSERT, a restore from a dump taken
            # before 0043, or a future outcome value that is not 'running' but
            # means it would each put two rows here, and a query that returns
            # "whichever" in that state is worse than one that returns the same
            # one twice.
            .order_by(WorkflowRunRow.started_at, WorkflowRunRow.id)
            .limit(1)
        )
        return busy

    async def awaiting(self, tenant_id: TenantId) -> tuple[tuple[str, int, str], ...]:
        query = (
            select(WorkflowRunStepRow.run_id, WorkflowRunStepRow.ord, WorkflowRunStepRow.says)
            .join(WorkflowRunRow, WorkflowRunRow.id == WorkflowRunStepRow.run_id)
            .where(
                WorkflowRunRow.tenant_id == tenant_id.value,
                # Only a run still in flight. The rig gated this list on the
                # runner's in-process `Approvals.waiting()` set, which is plan
                # 3's half; the storage half is this predicate, and without it
                # a step left `awaiting` on a run that was aborted or failed
                # sits in the supervisor's queue forever, asking for a tap that
                # can no longer let anything out.
                WorkflowRunRow.outcome == "running",
                WorkflowRunStepRow.verdict == "awaiting",
            )
            # Oldest wait first: this is the queue a supervisor works down, and
            # the run that has been parked longest is the one holding up a job.
            # The run id between the two, because two runs of one tenant can
            # be started in the same instant and their parked steps would
            # otherwise interleave differently on every read.
            .order_by(WorkflowRunRow.started_at, WorkflowRunRow.id, WorkflowRunStepRow.ord)
        )
        rows = (await self._session.execute(query)).all()
        return tuple((run_id, ord_, says) for run_id, ord_, says in rows)

    async def approve(self, run_id: str, ord_: int, *, at: str, device_id: str | None) -> bool:
        # DO NOTHING, the rig's OR IGNORE: a write rescued to the second rung
        # parks at the same step and takes a second tap, and the first
        # authorisation stands -- with the first approver's browser on it.
        # RETURNING rather than a rowcount, because whether this tap was the
        # one that authorised the step is the answer the caller wants.
        tapped = await self._session.execute(
            pg_insert(ApprovalRow)
            .values(run_id=run_id, ord=ord_, at=when(at), device_id=device_id)
            .on_conflict_do_nothing(index_elements=["run_id", "ord"])
            .returning(ApprovalRow.run_id)
        )
        return tapped.first() is not None

    async def approvals(self, run_id: str) -> tuple[tuple[int, str, str | None], ...]:
        query = (
            select(ApprovalRow.ord, ApprovalRow.at, ApprovalRow.device_id)
            .where(ApprovalRow.run_id == run_id)
            .order_by(ApprovalRow.ord)
        )
        rows = (await self._session.execute(query)).all()
        return tuple((ord_, at.isoformat(), device_id) for ord_, at, device_id in rows)

    async def fail_orphans(self, reason: str) -> int:
        now = datetime.now(tz=UTC).isoformat()
        query = self._rows().where(WorkflowRunRow.outcome == "running")
        rows = (
            await self._session.execute(
                query.order_by(WorkflowRunRow.started_at, WorkflowRunRow.id)
            )
        ).scalars()
        orphans = await self._with_steps(rows.all())
        for run in orphans:
            if run.steps:
                last = run.steps[-1]
                last.verdict, last.verdict_by, last.reason = "failed", "none", reason
            else:
                # The reason has to land somewhere the panel shows it, and a
                # run that died before its first step has nowhere.
                run.steps.append(
                    RunStep(order=0, says="", verdict="failed", verdict_by="none", reason=reason)
                )
            run.outcome = "failed"
            run.finished_at = now
            await self.save(run)
        return len(orphans)

    @staticmethod
    def _rows() -> Select[tuple[WorkflowRunRow]]:
        # ``save`` upserts with a Core statement, so a row this session had
        # already loaded would otherwise come back at its pre-save state.
        return select(WorkflowRunRow).execution_options(populate_existing=True)

    async def _with_steps(self, rows: Sequence[WorkflowRunRow]) -> tuple[WorkflowRun, ...]:
        """One query for every run's steps rather than one per run."""
        if not rows:
            return ()
        query = (
            select(WorkflowRunStepRow)
            .where(WorkflowRunStepRow.run_id.in_([row.id for row in rows]))
            .order_by(WorkflowRunStepRow.run_id, WorkflowRunStepRow.ord)
            .execution_options(populate_existing=True)
        )
        steps: defaultdict[str, list[RunStep]] = defaultdict(list)
        for step in (await self._session.execute(query)).scalars().all():
            steps[step.run_id].append(_row_to_step(step))
        return tuple(_row_to_run(row, steps[row.id]) for row in rows)
