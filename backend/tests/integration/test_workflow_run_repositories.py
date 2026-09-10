"""What a run of a mined workflow leaves behind, against real Postgres.

The rules under test are the rig's own -- ``rig/runs.py`` and the approval and
awaiting queries in ``rig/api.py``. They were SQLite there and are SQL here,
and a rule that changed on the way across is the failure this port exists to
avoid. The six run names come from ``new_agent_arch/tests/test_runs.py``; the
approval names come from the rig's route tests, kept where the rule under them
was a storage rule and renamed where the route half is plan 4's.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from sro.domain.execution.workflow_run import RunStep, WorkflowRun, new_run_id
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.infrastructure.db.models import WorkflowRunStepRow
from sro.infrastructure.db.repositories import SqlUnitOfWork

TENANT = TenantId("acme")
OTHER_TENANT = TenantId("other-corp")


def _run(**overrides: Any) -> WorkflowRun:
    fields: dict[str, Any] = {
        "id": new_run_id(),
        "tenant": TENANT.value,
        "workflow_id": "wfl_1",
        "device_id": "dev_1",
        "values": {"workArea": "THIRD"},
        "started_by": "form",
        "live": False,
        "allow_focus": True,
        "started_at": "2026-09-05T10:00:00+00:00",
    }
    fields.update(overrides)
    return WorkflowRun(**fields)


class TestWorkflowRuns:
    async def test_a_run_round_trips_with_every_step_and_every_withheld_write(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        run = _run(
            steps=[
                RunStep(
                    order=0,
                    says="type the code",
                    planned_by="gemini-3.8-flash",
                    sent={"kind": "ui.perform", "payload": {"action": "type", "value": "THIRD"}},
                    result={"performed": True, "matched_by": "component", "candidates": 1},
                    verdict="held",
                    verdict_by="screen",
                    reason="the field shows THIRD",
                    matched_by="component",
                    stale=False,
                    before_url="https://wms/x",
                    after_url="https://wms/x",
                    in_tokens=300,
                    out_tokens=40,
                    thought_tokens=10,
                    cost_usd=0.0004,
                    unpriced=False,
                ),
                RunStep(
                    order=1,
                    says="save",
                    planned_by="gemini-3.8-flash",
                    sent={"kind": "ui.perform", "payload": {"action": "click"}},
                    result={"withheld": True},
                    verdict="withheld",
                    verdict_by="dry",
                    reason="a dry run does not send writes",
                ),
            ],
            withheld=[
                {
                    "step": 1,
                    "method": "POST",
                    "url": "https://wms/data/WM/wm/workAreas",
                    "body": '{"workArea":"THIRD"}',
                }
            ],
            outcome="held",
            finished_at="2026-09-05T10:01:00+00:00",
            in_tokens=300,
            out_tokens=40,
            thought_tokens=10,
            cost_usd=0.0004,
        )

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflow_runs.get(TENANT, run.id)
            listed = await uow.workflow_runs.for_workflow(TENANT, "wfl_1")
            missing = await uow.workflow_runs.get(TENANT, "run_nobody")

        assert back == run
        assert listed == (run,)
        assert missing is None

    async def test_saving_again_replaces_the_steps_rather_than_appending(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A run is saved after every step so the panel can poll it; the second
        save must not double the first step -- and a step that leaves the
        record has to leave the store with it, which a per-step upsert keyed on
        (run_id, ord) would not do."""
        run = _run(steps=[RunStep(order=0, says="a", verdict="held", verdict_by="status")])

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            run.steps.append(RunStep(order=1, says="b", verdict="held", verdict_by="status"))
            await uow.workflow_runs.save(run)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            grown = await uow.workflow_runs.get(TENANT, run.id)

        assert grown is not None
        assert [step.order for step in grown.steps] == [0, 1]

        run.steps = run.steps[:1]
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            shrunk = await uow.workflow_runs.get(TENANT, run.id)

        assert shrunk is not None
        assert [step.order for step in shrunk.steps] == [0]

    async def test_a_step_that_sent_nothing_reads_back_as_sql_null(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Not the JSON scalar ``null``. JSONB stores ``None`` as that by
        default, and then ``sent IS NULL`` is false -- so every reader asking
        whether a step sent anything is told yes, about a step that sent
        nothing."""
        run = _run(steps=[RunStep(order=0, says="think", verdict="held")])

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        async with session_factory() as session:
            # Both columns asked the same way. `result is None` in Python is
            # also true of a JSON scalar `null`, so a Python-side assertion
            # about one and a SQL-side assertion about the other would leave
            # `result` untested for the very thing this test is about.
            empty = (
                await session.execute(
                    select(
                        WorkflowRunStepRow.sent.is_(None), WorkflowRunStepRow.result.is_(None)
                    ).where(WorkflowRunStepRow.run_id == run.id)
                )
            ).one()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflow_runs.get(TENANT, run.id)

        assert tuple(empty) == (True, True)
        assert back is not None
        assert (back.steps[0].sent, back.steps[0].result) == (None, None)

    async def test_the_flags_a_run_carries_survive_the_round_trip(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A run read back as a dry one would be re-offered as though it had
        never written; a cost read back as priced is a bill nobody knows to
        distrust."""
        run = _run(
            live=True,
            allow_focus=False,
            unpriced=True,
            steps=[
                RunStep(order=0, says="a", verdict="held", stale=True, unpriced=True, cost_usd=0.0)
            ],
        )

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflow_runs.get(TENANT, run.id)

        assert back is not None
        assert (back.live, back.allow_focus, back.unpriced) == (True, False, True)
        assert (back.steps[0].stale, back.steps[0].unpriced) == (True, True)

    async def test_another_tenants_run_is_not_found(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        run = _run()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflow_runs.get(OTHER_TENANT, run.id) is None
            assert await uow.workflow_runs.for_workflow(OTHER_TENANT, "wfl_1") == ()

    async def test_the_browser_already_driving_a_run_is_the_one_still_running(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """One browser, one hand. Two runs driving the same window interleave
        their clicks into a form neither of them can then read back."""
        run = _run()
        elsewhere = _run(tenant=OTHER_TENANT.value)

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.workflow_runs.save(elsewhere)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            busy = await uow.workflow_runs.in_flight(TENANT, DeviceId("dev_1"))
            other_browser = await uow.workflow_runs.in_flight(TENANT, DeviceId("dev_2"))

        assert busy == run.id
        assert other_browser is None

        run.outcome = "held"
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflow_runs.in_flight(TENANT, DeviceId("dev_1")) is None

    async def test_the_tally_is_one_group_by_and_never_loads_a_run(
        self,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """The half of the N+1 fix that only the statements can show.

        ``shapes_for``'s unit guard counts calls to ``tallies``, and the
        contract compares its answer. A ``tallies`` reimplemented as "select
        this tenant's run rows and count them in Python" passes both -- one
        call, no ``for_workflow``, identical mapping -- while restoring the
        entire cost the port exists to remove: every run row of every
        workflow, fetched to produce two integers. What makes it a fix rather
        than a rename is that Postgres does the counting, and that is a fact
        about the statements, not about the answer.

        Three workflows of four runs, each with a step, so a load would be
        visible twice over: as a second statement, and as the step table.
        """
        async with SqlUnitOfWork(session_factory) as uow:
            for which in range(3):
                for _ in range(4):
                    await uow.workflow_runs.save(
                        _run(
                            workflow_id=f"wfl_{which}",
                            outcome="held" if which else "failed",
                            steps=[RunStep(order=0, says="save", verdict="held")],
                        )
                    )
            await uow.commit()

        asked: list[str] = []

        def watch(
            connection: Any,
            cursor: Any,
            statement: str,
            parameters: Any,
            context: Any,
            executemany: bool,
        ) -> None:
            asked.append(" ".join(statement.split()))

        event.listen(engine.sync_engine, "before_cursor_execute", watch)
        try:
            async with SqlUnitOfWork(session_factory) as uow:
                counted = await uow.workflow_runs.tallies(TENANT)
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", watch)

        assert dict(counted) == {"wfl_0": (4, 0), "wfl_1": (4, 4), "wfl_2": (4, 4)}
        assert len(asked) == 1, f"one GROUP BY, not a load and a count: {asked}"
        assert "GROUP BY" in asked[0].upper()
        assert "workflow_run_steps" not in asked[0], "nothing is loaded, so no step is either"


class TestOrphans:
    async def test_a_run_still_running_when_the_rig_starts_is_failed_and_says_why(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        orphan = _run(steps=[RunStep(order=0, says="s", verdict="held")])
        # A second browser, because one browser holds one running run since
        # migration 0043 -- and because that is the shape of the thing being
        # swept: one process died, and every browser it was driving is orphaned.
        bare = _run(device_id="dev_2")
        done = _run(outcome="held", finished_at="2026-09-05T10:01:00+00:00")
        # Across tenants, unlike every other read here: nobody is making the
        # request at startup, and a run left running in one tenant would go on
        # 409-ing its browser however green the other tenant is.
        elsewhere = _run(tenant=OTHER_TENANT.value)

        async with SqlUnitOfWork(session_factory) as uow:
            for run in (orphan, bare, done, elsewhere):
                await uow.workflow_runs.save(run)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            swept = await uow.workflow_runs.fail_orphans("the rig restarted")
            await uow.commit()

        assert swept == 3

        async with SqlUnitOfWork(session_factory) as uow:
            failed = await uow.workflow_runs.get(TENANT, orphan.id)
            stepless = await uow.workflow_runs.get(TENANT, bare.id)
            untouched = await uow.workflow_runs.get(TENANT, done.id)
            far = await uow.workflow_runs.get(OTHER_TENANT, elsewhere.id)

        assert failed is not None and failed.outcome == "failed" and failed.finished_at
        assert failed.steps[-1].verdict == "failed"
        assert failed.steps[-1].reason == "the rig restarted"
        assert stepless is not None and stepless.steps[0].reason == "the rig restarted"
        assert untouched is not None and untouched.outcome == "held"
        assert far is not None and far.outcome == "failed"

    async def test_an_orphan_with_no_step_at_all_gets_one_that_says_who_failed(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The reason has to land somewhere the panel shows it, and a run that
        died before its first step has nowhere -- so it gets step zero."""
        bare = _run()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(bare)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.fail_orphans("the rig restarted")
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            stepless = await uow.workflow_runs.get(TENANT, bare.id)

        assert stepless is not None
        [only] = stepless.steps
        assert (only.order, only.says) == (0, "")
        assert (only.verdict, only.verdict_by) == ("failed", "none")
        # UTC, spelled out: a naive local timestamp beside the UTC ones every
        # other writer produces reads as a run that finished hours before it
        # started.
        assert stepless.finished_at is not None and stepless.finished_at.endswith("+00:00")

    async def test_the_reason_lands_on_the_step_the_orphan_died_in(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        orphan = _run(steps=[RunStep(order=0, says="s", verdict="held", verdict_by="status")])

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(orphan)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.fail_orphans("the rig restarted")
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            failed = await uow.workflow_runs.get(TENANT, orphan.id)

        assert failed is not None and len(failed.steps) == 1
        assert (failed.steps[0].verdict, failed.steps[0].verdict_by) == ("failed", "none")


class TestApprovals:
    async def test_the_first_tap_wins_and_a_second_on_the_same_step_is_not_a_second_authorisation(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A write rescued to the second rung parks at the same step and takes
        a second tap; the first authorisation stands."""
        run = _run(steps=[RunStep(order=0, says="save", verdict="awaiting")])

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            first = await uow.workflow_runs.approve(
                run.id, 0, at="2026-09-05T10:02:00+00:00", device_id="dev_1"
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            second = await uow.workflow_runs.approve(
                run.id, 0, at="2026-09-05T10:09:00+00:00", device_id="dev_9"
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            given = await uow.workflow_runs.approvals(run.id)

        assert first is True
        assert second is False
        assert given == ((0, "2026-09-05T10:02:00+00:00", "dev_1"),)

    async def test_an_approval_names_the_browser_whose_panel_the_tap_came_from(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A bare POST is a tap, so the browser is optional -- but when the
        panel sends it, the record says which browser let the write out."""
        run = _run(
            steps=[
                RunStep(order=0, says="save", verdict="awaiting"),
                RunStep(order=1, says="confirm", verdict="awaiting"),
            ]
        )

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.workflow_runs.approve(
                run.id, 0, at="2026-09-05T10:02:00+00:00", device_id="dev_7"
            )
            await uow.workflow_runs.approve(
                run.id, 1, at="2026-09-05T10:03:00+00:00", device_id=None
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            given = await uow.workflow_runs.approvals(run.id)

        assert given == (
            (0, "2026-09-05T10:02:00+00:00", "dev_7"),
            (1, "2026-09-05T10:03:00+00:00", None),
        )

    async def test_a_run_waiting_on_a_person_is_found_by_the_step_that_is_awaiting(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The list a supervisor reads to see what needs them right now, from
        any browser, not the one the run is in."""
        parked = _run(
            steps=[
                RunStep(order=0, says="type the code", verdict="held"),
                RunStep(order=1, says="save the work area", verdict="awaiting"),
            ]
        )
        # A second browser: one browser holds one running run since migration
        # 0043, and "from any browser" is what this read is for.
        moving = _run(
            device_id="dev_2", steps=[RunStep(order=0, says="type the code", verdict="held")]
        )
        # A run nobody can answer any more: the tap it is asking for could not
        # let anything out, and without a liveness predicate it would sit in
        # the supervisor's queue forever.
        over = _run(
            outcome="aborted",
            finished_at="2026-09-05T10:04:00+00:00",
            steps=[RunStep(order=0, says="a write nobody let out", verdict="awaiting")],
        )
        elsewhere = _run(
            tenant=OTHER_TENANT.value,
            steps=[RunStep(order=0, says="somebody else's write", verdict="awaiting")],
        )

        async with SqlUnitOfWork(session_factory) as uow:
            for run in (parked, moving, over, elsewhere):
                await uow.workflow_runs.save(run)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            waiting = await uow.workflow_runs.awaiting(TENANT)

        assert waiting == ((parked.id, 1, "save the work area"),)
