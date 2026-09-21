"""Mined workflows on Postgres: their steps, their passes, and what they earned.

The rules here are the rig's -- ``rig/workflows.py``, ``rig/effects.py``, the
``passes`` insert and the ``rekey`` update in ``rig/mine.py``, the
``workflow_stale`` insert and delete in ``rig/runner.py``, and the stale count
in ``rig/api.py``. They were SQLite there. What had to be translated rather
than copied is marked where it happens:

* ``INSERT OR REPLACE`` becomes ``ON CONFLICT DO UPDATE`` on a named conflict
  target, as in ``workflow_runs``. SQLite's form swallows *every* constraint;
  naming the target means a different constraint failing is still an error
  rather than a silent no-op.
* The clocks are ``timestamptz`` where the rig kept text, because both indexes
  order on one and an offset-less string sorts beside an offset-bearing one
  with neither wrong. The records still carry ISO strings, so this converts on
  both edges.
* ``earned`` was a boolean the store computed. Here the store assembles the
  evidence -- one ``RunProof`` per live held run -- and ``earned_from`` in
  ``sro.domain.execution.belts`` decides. The rule about how many runs and
  which belts count is the domain's; walking the rows is this file's.
* The gate on ``record_effect`` is likewise the domain's ``state_verified``
  rather than a second copy of the belt list. A picture is not an effect, and
  that must be one sentence in one place.

The row-to-record mapping lives here rather than in ``mappers.py``: a
repository's mapping belongs with the repository, and these shapes are read by
nothing else.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sro.application.ports.repositories import WorkflowRepository
from sro.domain.execution.belts import RunProof, state_verified
from sro.domain.execution.learned_step import LearnedStep, Taught, changed_by
from sro.domain.observation.identity import ShapeKey
from sro.domain.observation.mining import MiningPass
from sro.domain.shared.errors import Conflict, NotFound
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.repeats import Repeat
from sro.domain.skill.workflow import Step, Workflow
from sro.infrastructure.db.codec import when
from sro.infrastructure.db.models import (
    MiningPassRow,
    WorkflowEffectRow,
    WorkflowLearnedHistoryRow,
    WorkflowLearnedRow,
    WorkflowRow,
    WorkflowRunRow,
    WorkflowRunStepRow,
    WorkflowStaleRow,
    WorkflowStepRow,
)


def _workflow_values(workflow: Workflow) -> dict[str, Any]:
    return {
        "id": workflow.id,
        "tenant_id": workflow.tenant,
        "pass_id": workflow.pass_id,
        "title": workflow.title,
        "narrative": workflow.narrative,
        "systems": list(workflow.systems),
        "parameters": list(workflow.parameters),
        "shape_key": [list(entry) for entry in workflow.shape_key],
        "same_as": workflow.same_as,
        "repeat": (
            None
            if workflow.repeat is None
            else {
                "first_step": workflow.repeat.first_step,
                "last_step": workflow.repeat.last_step,
            }
        ),
        "created_at": datetime.now(tz=UTC),
    }


def _step_values(workflow_id: str, step: Step) -> dict[str, Any]:
    return {
        "workflow_id": workflow_id,
        "ord": step.order,
        "says": step.says,
        "system": step.system,
        "cites": list(step.cites),
        "parameters": list(step.parameters),
        "uses": list(step.uses),
    }


def _row_to_step(row: WorkflowStepRow) -> Step:
    return Step(
        order=row.ord,
        says=row.says,
        system=row.system,
        cites=list(row.cites),
        parameters=list(row.parameters),
        # An older row has no `uses` at all, and a job that predates the column
        # used nothing -- which is what an absent one honestly means.
        uses=list(row.uses or []),
    )


def _row_to_workflow(row: WorkflowRow, steps: list[Step]) -> Workflow:
    return Workflow(
        id=row.id,
        tenant=row.tenant_id,
        title=row.title,
        narrative=row.narrative,
        systems=list(row.systems),
        steps=steps,
        parameters=list(row.parameters),
        shape_key=[list(entry) for entry in row.shape_key],
        same_as=row.same_as,
        pass_id=row.pass_id,
        repeat=(
            Repeat(
                first_step=int(row.repeat["first_step"]),
                last_step=int(row.repeat["last_step"]),
            )
            if isinstance(row.repeat, dict)
            else None
        ),
    )


def _row_to_pass(row: MiningPassRow) -> MiningPass:
    return MiningPass(
        id=row.id,
        tenant=row.tenant_id,
        started_at=row.started_at.isoformat(),
        in_tokens=row.in_tokens,
        out_tokens=row.out_tokens,
        thought_tokens=row.thought_tokens,
        cost_usd=row.cost_usd,
        unpriced=row.unpriced,
        proposed=row.proposed,
        kept=row.kept,
        rejected=row.rejected,
        learned_parameters=row.learned_parameters,
        coverage=row.coverage,
        skew=row.skew,
        lopsided=row.lopsided,
        window_size=row.window_size,
        left_out=row.left_out,
        unplaced=row.unplaced,
        error=row.error,
    )


logger = logging.getLogger(__name__)


class SqlWorkflowRepository(WorkflowRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, workflow: Workflow) -> None:
        statement = pg_insert(WorkflowRow).values(**_workflow_values(workflow))
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["id"],
                # Every column but the key, ``created_at`` included -- which is
                # what INSERT OR REPLACE did, and it is kept rather than
                # quietly improved: a workflow identity resolution re-saves
                # moves to the end of ``known``, and the miner resolving in a
                # different order here than in the rig is exactly the drift
                # this port exists to avoid.
                set_={
                    column.name: statement.excluded[column.name]
                    for column in WorkflowRow.__table__.columns
                    if column.name != "id"
                },
            )
        )
        # Deleted and reinserted rather than upserted one by one: a step the
        # merge dropped has to leave the store with it, and an upsert would
        # leave it behind.
        await self._session.execute(
            delete(WorkflowStepRow).where(WorkflowStepRow.workflow_id == workflow.id)
        )
        if workflow.steps:
            await self._session.execute(
                pg_insert(WorkflowStepRow).values(
                    [_step_values(workflow.id, step) for step in workflow.steps]
                )
            )

    async def known(self, tenant_id: TenantId) -> tuple[Workflow, ...]:
        query = (
            select(WorkflowRow)
            .where(WorkflowRow.tenant_id == tenant_id.value)
            # The id breaks a tie the rig never had to: two workflows of one
            # pass are saved microseconds apart there and can share an instant
            # here, and an order that is not total is an order that changes
            # between reads.
            .order_by(WorkflowRow.created_at, WorkflowRow.id)
            # ``save`` upserts with a Core statement, so a row this session had
            # already loaded would otherwise come back at its pre-save state.
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(query)).scalars().all()
        if not rows:
            return ()
        steps = await self._steps_of([row.id for row in rows])
        return tuple(_row_to_workflow(row, steps[row.id]) for row in rows)

    async def get(self, tenant_id: TenantId, workflow_id: str) -> Workflow:
        query = (
            select(WorkflowRow)
            .where(WorkflowRow.tenant_id == tenant_id.value, WorkflowRow.id == workflow_id)
            .execution_options(populate_existing=True)
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"workflow {workflow_id} was not found")
        steps = await self._steps_of([row.id])
        return _row_to_workflow(row, steps[row.id])

    async def rekey(self, tenant_id: TenantId, workflow_id: str, key: ShapeKey) -> None:
        await self._session.execute(
            update(WorkflowRow)
            .where(WorkflowRow.tenant_id == tenant_id.value, WorkflowRow.id == workflow_id)
            .values(shape_key=[list(entry) for entry in key])
        )

    async def add_pass(self, mining_pass: MiningPass) -> None:
        # A plain insert, as in the rig, and no ON CONFLICT: a pass id is
        # minted per reading, so a second row under one id would be one model
        # call billed twice. Reported as a Conflict rather than escaping as an
        # IntegrityError out of somebody else's commit.
        try:
            await self._session.execute(
                pg_insert(MiningPassRow).values(
                    id=mining_pass.id,
                    tenant_id=mining_pass.tenant,
                    started_at=when(mining_pass.started_at),
                    in_tokens=mining_pass.in_tokens,
                    out_tokens=mining_pass.out_tokens,
                    thought_tokens=mining_pass.thought_tokens,
                    cost_usd=mining_pass.cost_usd,
                    unpriced=mining_pass.unpriced,
                    proposed=mining_pass.proposed,
                    kept=mining_pass.kept,
                    rejected=mining_pass.rejected,
                    learned_parameters=mining_pass.learned_parameters,
                    coverage=mining_pass.coverage,
                    skew=mining_pass.skew,
                    lopsided=mining_pass.lopsided,
                    window_size=mining_pass.window_size,
                    left_out=mining_pass.left_out,
                    unplaced=mining_pass.unplaced,
                    error=mining_pass.error,
                )
            )
        except IntegrityError as clash:
            await self._session.rollback()
            raise Conflict(f"mining pass {mining_pass.id} is already stored") from clash

    async def passes(self, tenant_id: TenantId) -> tuple[MiningPass, ...]:
        query = (
            select(MiningPassRow)
            .where(MiningPassRow.tenant_id == tenant_id.value)
            .order_by(MiningPassRow.started_at, MiningPassRow.id)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(_row_to_pass(row) for row in rows)

    async def mark_stale(
        self, workflow_id: str, ord_: int, *, matched_by: str | None, noticed_at: str
    ) -> None:
        # The rig's INSERT OR REPLACE: one row per step, so a job run every
        # morning reports the same weak step once rather than daily. The later
        # notice wins, because the last rung a step matched on is the current
        # answer about that step.
        statement = pg_insert(WorkflowStaleRow).values(
            workflow_id=workflow_id,
            ord=ord_,
            matched_by=matched_by,
            noticed_at=when(noticed_at),
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["workflow_id", "ord"],
                set_={
                    "matched_by": statement.excluded.matched_by,
                    "noticed_at": statement.excluded.noticed_at,
                },
            )
        )

    async def remember_limit(
        self, workflow_id: str, ord_: int, holds: int, *, by_run: str = ""
    ) -> None:
        """What this step's box will take, learnt once.

        Its own method rather than a field on `remember_locator`, because the
        two are learnt at different moments and about different things: a
        locator is learnt when the recorded identity failed, and a limit is
        learnt on a step whose locator matched perfectly well. Writing them
        together would mean a truncation erasing a locator, or a locator
        erasing a limit -- so each writes only its own columns, and a step can
        carry both.
        """
        # A limit is learnt on a step whose locator matched perfectly well, so
        # what is compared here carries the locator this step already has --
        # otherwise every measured limit would read as a locator being erased.
        already = next(
            (one for one in await self.learned_for(workflow_id) if one.ord == ord_), None
        )
        await self._keep_what_changed(
            workflow_id,
            LearnedStep(
                ord=ord_,
                strategy=already.strategy if already else "",
                query=already.query if already else "",
                found_by="typed",
                holds=holds,
            ),
            by_run=by_run,
        )
        statement = pg_insert(WorkflowLearnedRow).values(
            workflow_id=workflow_id,
            ord=ord_,
            # Empty rather than absent, for a step that has never needed a
            # locator learnt: the columns are not null, and "" is honestly what
            # is known about a locator nobody has had to find.
            strategy="",
            query="",
            found_by="typed",
            holds=holds,
            learned_at=datetime.now(tz=UTC),
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["workflow_id", "ord"],
                set_={
                    "holds": statement.excluded.holds,
                    "learned_at": statement.excluded.learned_at,
                },
            )
        )

    async def remember_locator(
        self, workflow_id: str, learned: LearnedStep, *, by_run: str = ""
    ) -> None:
        # Before the upsert, because the upsert is what destroys the answer it
        # is compared against.
        await self._keep_what_changed(workflow_id, learned, by_run=by_run)
        # The stale row's shape, and for its reason: one row per step, the
        # later notice winning, because the last locator that worked is the
        # current answer about that step.
        statement = pg_insert(WorkflowLearnedRow).values(
            workflow_id=workflow_id,
            ord=learned.ord,
            strategy=learned.strategy,
            query=learned.query,
            found_by=learned.found_by,
            learned_at=datetime.now(tz=UTC),
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["workflow_id", "ord"],
                set_={
                    "strategy": statement.excluded.strategy,
                    "query": statement.excluded.query,
                    "found_by": statement.excluded.found_by,
                    "learned_at": statement.excluded.learned_at,
                },
            )
        )

    async def _keep_what_changed(
        self, workflow_id: str, now: LearnedStep, *, by_run: str = ""
    ) -> None:
        """Append what this step just learned that it did not already know.

        Read-then-write, and deliberately not a transaction of its own: it runs
        inside the run's, so a history row and the learned row it describes
        arrive together or not at all. A history that disagrees with the thing
        it is a history of is worse than none.

        Silent on every failure. This is a record FOR somebody, and a run that
        fell over because it could not write one would have turned reading into
        a reason to stop working.
        """
        try:
            was = next(
                (one for one in await self.learned_for(workflow_id) if one.ord == now.ord),
                None,
            )
            at = datetime.now(tz=UTC)
            for change in changed_by(was, now, by_run=by_run):
                self._session.add(
                    WorkflowLearnedHistoryRow(
                        # The step and the moment, which is what makes it
                        # unique: one step cannot change its mind twice in the
                        # same microsecond, and a uuid here would be a second
                        # thing to explain.
                        id=f"lrn_{workflow_id}_{change.ord}_{change.about}_{at.timestamp()}"[:64],
                        workflow_id=workflow_id,
                        ord=change.ord,
                        about=change.about,
                        was=change.was,
                        now=change.now,
                        by_run=change.by_run,
                        found_by=change.found_by,
                        at=at,
                    )
                )
        except Exception:
            logger.exception("what %s taught itself could not be written down", workflow_id)

    async def taught_itself(self, workflow_id: str, limit: int = 50) -> tuple[Taught, ...]:
        """What this job has changed its mind about, newest first.

        The one query the history is for. A history nobody can read in one page
        is a log, which is why there is a limit and why it is small.
        """
        rows = (
            await self._session.execute(
                select(WorkflowLearnedHistoryRow)
                .where(WorkflowLearnedHistoryRow.workflow_id == workflow_id)
                .order_by(WorkflowLearnedHistoryRow.at.desc())
                .limit(limit)
            )
        ).scalars()
        return tuple(
            Taught(
                ord=row.ord,
                about=row.about,
                was=row.was,
                now=row.now,
                by_run=row.by_run,
                found_by=row.found_by,
            )
            for row in rows
        )

    async def learned_for(self, workflow_id: str) -> tuple[LearnedStep, ...]:
        rows = (
            await self._session.execute(
                select(WorkflowLearnedRow).where(WorkflowLearnedRow.workflow_id == workflow_id)
            )
        ).scalars()
        return tuple(
            LearnedStep(
                ord=row.ord,
                strategy=row.strategy,
                query=row.query,
                found_by=row.found_by,
                holds=row.holds,
            )
            for row in rows
        )

    async def clear_stale(self, workflow_id: str, ord_: int) -> None:
        await self._session.execute(
            delete(WorkflowStaleRow).where(
                WorkflowStaleRow.workflow_id == workflow_id, WorkflowStaleRow.ord == ord_
            )
        )

    async def stale_count(self, workflow_id: str) -> int:
        found = await self._session.scalar(
            select(func.count())
            .select_from(WorkflowStaleRow)
            .where(WorkflowStaleRow.workflow_id == workflow_id)
        )
        return int(found or 0)

    async def record_effect(
        self, workflow_id: str, *, run_id: str, ord_: int, verified_by: str, at: str
    ) -> None:
        # The gate, before the write: a verdict that did not see the state
        # itself is not an effect, and a screenshot is not evidence anything
        # was written. Dropped rather than stored-and-filtered, so nothing
        # downstream has to remember to ask again.
        if not state_verified(verified_by):
            return
        statement = pg_insert(WorkflowEffectRow).values(
            workflow_id=workflow_id,
            run_id=run_id,
            ord=ord_,
            verified_by=verified_by,
            at=when(at),
        )
        # One write of one run of one job is one effect however many times it
        # is verified -- a write rescued to the second rung verifies at the
        # same step, and that is not two proofs.
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["workflow_id", "run_id", "ord"],
                set_={
                    "verified_by": statement.excluded.verified_by,
                    "at": statement.excluded.at,
                },
            )
        )

    async def forget_effects(self, workflow_id: str) -> int:
        # RETURNING rather than ``rowcount``, as everywhere else here: how many
        # a job had earned is the answer the caller wants, and a driver's
        # rowcount is not the same promise across drivers.
        gone = await self._session.execute(
            delete(WorkflowEffectRow)
            .where(WorkflowEffectRow.workflow_id == workflow_id)
            .returning(WorkflowEffectRow.run_id)
        )
        return len(gone.all())

    async def proofs(self, tenant_id: TenantId, workflow_id: str) -> tuple[RunProof, ...]:
        runs = (
            await self._session.execute(
                select(WorkflowRunRow.id)
                .where(
                    WorkflowRunRow.tenant_id == tenant_id.value,
                    WorkflowRunRow.workflow_id == workflow_id,
                    WorkflowRunRow.live.is_(True),
                    WorkflowRunRow.outcome == "held",
                )
                .order_by(WorkflowRunRow.started_at, WorkflowRunRow.id)
            )
        ).scalars()
        run_ids = list(runs.all())
        if not run_ids:
            return ()

        # Three queries whatever the number of runs, rather than two per run.
        wrote: defaultdict[str, set[int]] = defaultdict(set)
        steps = await self._session.execute(
            select(
                WorkflowRunStepRow.run_id, WorkflowRunStepRow.ord, WorkflowRunStepRow.result
            ).where(WorkflowRunStepRow.run_id.in_(run_ids))
        )
        for run_id, ord_, result in steps.all():
            # The step's own marker, set by the runner at send time: SQL cannot
            # ask ``writes()``, and the evidence a later reader would have to
            # ask it about may have been re-mined by then. Read for truth here
            # rather than as ``->>'wrote' = 'true'`` in the WHERE, so the
            # predicate stays the rig's own -- truthy on whatever the runner
            # marks with -- rather than a narrower one that would silently miss
            # a writer emitting 1 or "yes".
            if result and result.get("wrote"):
                wrote[run_id].add(ord_)

        verified: defaultdict[str, set[int]] = defaultdict(set)
        effects = await self._session.execute(
            select(WorkflowEffectRow.run_id, WorkflowEffectRow.ord).where(
                WorkflowEffectRow.workflow_id == workflow_id,
                WorkflowEffectRow.run_id.in_(run_ids),
            )
        )
        for run_id, ord_ in effects.all():
            verified[run_id].add(ord_)

        return tuple(
            RunProof(
                run_id=run_id,
                wrote=frozenset(wrote[run_id]),
                verified=frozenset(verified[run_id]),
            )
            for run_id in run_ids
        )

    async def _steps_of(self, workflow_ids: list[str]) -> defaultdict[str, list[Step]]:
        """One query for every workflow's steps rather than one per workflow."""
        query = (
            select(WorkflowStepRow)
            .where(WorkflowStepRow.workflow_id.in_(workflow_ids))
            .order_by(WorkflowStepRow.workflow_id, WorkflowStepRow.ord)
            .execution_options(populate_existing=True)
        )
        steps: defaultdict[str, list[Step]] = defaultdict(list)
        for row in (await self._session.execute(query)).scalars().all():
            steps[row.workflow_id].append(_row_to_step(row))
        return steps
