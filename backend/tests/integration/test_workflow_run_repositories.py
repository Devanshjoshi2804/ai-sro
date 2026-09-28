"""What a run of a mined workflow leaves behind, against real Postgres.

The rules under test are the rig's own -- ``rig/runs.py`` and the approval and
awaiting queries in ``rig/api.py``. They were SQLite there and are SQL here,
and a rule that changed on the way across is the failure this port exists to
avoid. The six run names come from ``new_agent_arch/tests/test_runs.py``; the
approval names come from the rig's route tests, kept where the rule under them
was a storage rule and renamed where the route half is plan 4's.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from sro.application.context import RequestContext
from sro.domain.execution.run import Run, RunId
from sro.domain.execution.workflow_run import RunStep, WorkflowRun, new_run_id
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import DeviceId, PrincipalId, SkillId, TenantId
from sro.domain.skill import PromotionStage
from sro.infrastructure.db.models import WorkflowRunStepRow
from sro.infrastructure.db.repositories import SqlUnitOfWork


class _Clock:
    """Enough of a clock for the one method under test."""

    def now(self) -> datetime:
        return datetime(2026, 9, 18, tzinfo=UTC)


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


def _skill_run(run_id: str, **overrides: Any) -> Run:
    """One skill run, the older path's kind, with the fields its index reads."""
    fields: dict[str, Any] = {
        "id": RunId(run_id),
        "tenant_id": TENANT,
        "skill_id": SkillId("skl_1"),
        "skill_version": 1,
        "stage": PromotionStage.SHADOW,
        "parameters": {},
        "requested_by": PrincipalId("operator"),
        "started_at": datetime(2026, 9, 5, 10, tzinfo=UTC),
        "device_id": DeviceId("dev_1"),
    }
    fields.update(overrides)
    return Run(**fields)


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

    async def test_saving_again_upserts_the_steps_rather_than_appending(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A run is saved after every step so the panel can poll it; the second
        save must not double the first step. Each step is upserted by
        `(run_id, ord)` rather than deleted and reinserted, so a save that
        carries fewer steps than the row already has never erases the rest --
        `test_a_stale_save_does_not_erase_a_step_the_worker_added` is the
        failure mode a delete-then-insert would still have."""
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

    async def test_a_stale_save_does_not_erase_a_step_the_worker_added(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A stale API save carries only the steps its own stale copy knew
        about -- one -- saved after a worker has since appended a second one
        to the same run. The worker's step must survive it, the same way
        C1 keeps a stale save from rolling `progress` back."""
        run = _run(steps=[RunStep(order=0, says="a", verdict="held", verdict_by="status")])

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        # A caller's stale copy: loaded before the worker's step below.
        async with SqlUnitOfWork(session_factory) as uow:
            stale_copy = await uow.workflow_runs.get(TENANT, run.id)
            assert stale_copy is not None

        # The worker appends and saves its own, newer copy.
        async with SqlUnitOfWork(session_factory) as uow:
            worker_copy = await uow.workflow_runs.get(TENANT, run.id)
            assert worker_copy is not None
            worker_copy.steps.append(
                RunStep(order=1, says="b", verdict="held", verdict_by="status")
            )
            await uow.workflow_runs.save(worker_copy)
            await uow.commit()

        # The stale copy -- still just step 0 -- is saved back.
        async with SqlUnitOfWork(session_factory) as uow:
            stale_copy.watched = True
            await uow.workflow_runs.save(stale_copy)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflow_runs.get(TENANT, run.id)

        assert back is not None
        assert back.watched is True, "the stale save's own change still landed"
        assert [step.order for step in back.steps] == [0, 1], (
            "the worker's step must survive a stale save that never carried it"
        )

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

    async def test_which_run_took_this_one_back_survives_the_round_trip(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Both directions of the mapping, and both answers of the lookup: an
        undo that held is what refuses a second press, and one that failed left
        the record exactly where it was."""
        made = _run()
        undo = _run(device_id="dev_2", undoes_run=made.id, outcome="held")

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(made)
            await uow.workflow_runs.save(undo)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            read = await uow.workflow_runs.get(TENANT, undo.id)
            assert read is not None and read.undoes_run == made.id
            assert (await uow.workflow_runs.get(TENANT, made.id)) is not None
            assert (await uow.workflow_runs.get(TENANT, made.id)).undoes_run is None
            assert await uow.workflow_runs.taken_back_by(TENANT, made.id) == undo.id
            # Scoped, like every other read here.
            assert await uow.workflow_runs.taken_back_by(OTHER_TENANT, made.id) is None
            # And nothing has taken back the undo itself.
            assert await uow.workflow_runs.taken_back_by(TENANT, undo.id) is None

        # An ended outcome is never rewritten (D4), so an undo that failed is its
        # own run from the start, not the held undo turned failed.
        other = _run(device_id="dev_3")
        failed = _run(device_id="dev_4", undoes_run=other.id, outcome="failed")
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(other)
            await uow.workflow_runs.save(failed)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            # An undo that did not work is not a record that is gone, and the
            # second press is the one that might still remove it.
            assert await uow.workflow_runs.taken_back_by(TENANT, other.id) is None

    async def test_a_run_is_found_again_by_the_conversation_it_answers_to(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The question is asked inside a JSON document, which is the reason
        this is here and not only against the fake: `awaiting ->> 'thread'` is
        a string nothing type-checks, and a typo in it answers "no run is
        waiting" for every reply anybody ever sends.
        """
        waiting = _run(
            device_id="dev_a",
            outcome="stopped",
            needs=["Customer Type"],
            awaiting={"server": "gmail", "thread": "t-9", "until": "2099-01-01T00:00:00+00:00"},
        )
        # Started LATER, so the newest-first ordering would hand this one back
        # if the tenant clause were missing: a thread id is somebody else's
        # mail, and a reply to it resuming this tenant's run is the boundary
        # undone by an ORDER BY.
        elsewhere = _run(
            device_id="dev_b",
            tenant=OTHER_TENANT.value,
            outcome="stopped",
            started_at="2026-09-06T10:00:00+00:00",
            awaiting={"server": "gmail", "thread": "t-9", "until": "2099-01-01T00:00:00+00:00"},
        )
        # A run whose stored thread is blank. Nothing writes one -- `waiting_on`
        # refuses to build a wait with no conversation in it -- but a hand
        # edit or an older row can, and a blank matching a blank is one run
        # answering a reply to something else entirely.
        blank = _run(
            device_id="dev_e",
            outcome="stopped",
            awaiting={"server": "gmail", "thread": "", "until": "2099-01-01T00:00:00+00:00"},
        )
        plain = _run(device_id="dev_c", outcome="held")

        async with SqlUnitOfWork(session_factory) as uow:
            for one in (waiting, elsewhere, blank, plain):
                await uow.workflow_runs.save(one)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            found = await uow.workflow_runs.waiting_on(TENANT, server="gmail", thread="t-9")
            # The document is read back whole, not only matched on.
            assert found is not None and found.id == waiting.id
            assert found.awaiting == waiting.awaiting
            assert found.needs == ["Customer Type"]
            # Another tenant's conversation is not this tenant's.
            assert found.tenant == TENANT.value

            # A thread nobody named, a connector nobody named, and a run that
            # named neither: three ways of asking about nothing.
            assert await uow.workflow_runs.waiting_on(TENANT, server="gmail", thread="t-8") is None
            assert await uow.workflow_runs.waiting_on(TENANT, server="slack", thread="t-9") is None
            assert await uow.workflow_runs.waiting_on(TENANT, server="gmail", thread="") is None
            assert await uow.workflow_runs.waiting_on(TENANT, server="", thread="t-9") is None

    async def test_a_drafted_run_asking_who_its_mail_goes_to_waits_on_its_thread(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The draft path's `recipient` question stands on a stopped run, and a
        reply on its thread must find it; a stopped run asking anything else,
        or nothing, is not waiting."""
        wait = {"server": "gmail", "thread": "t-7", "until": "2099-01-01T00:00:00+00:00"}
        who = _run(device_id="dev_h", outcome="stopped", awaiting=wait)
        other = _run(device_id="dev_i", outcome="stopped", awaiting={**wait, "thread": "t-4"})
        async with SqlUnitOfWork(session_factory) as uow:
            for one in (who, other):
                await uow.workflow_runs.save(one)
            await uow.workflow_runs.record_progress(
                TENANT, who.id, {"asking": {"id": "q-1", "kind": "recipient", "text": "who?"}}
            )
            await uow.workflow_runs.record_progress(
                TENANT, other.id, {"asking": {"id": "q-2", "kind": "value", "text": "what?"}}
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            found = await uow.workflow_runs.waiting_on(TENANT, server="gmail", thread="t-7")
            assert found is not None and found.id == who.id
            assert await uow.workflow_runs.waiting_on(TENANT, server="gmail", thread="t-4") is None

    async def test_a_drafted_run_asking_what_its_mail_says_waits_on_its_thread(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """S4 M7: the draft path's `mail_body` question stands on a stopped run
        too. A reply on its thread finds the run -- which the mail door then
        never answers -- rather than being read as a new request."""
        wait = {"server": "gmail", "thread": "t-3", "until": "2099-01-01T00:00:00+00:00"}
        body = _run(device_id="dev_j", outcome="stopped", awaiting=wait)
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(body)
            await uow.workflow_runs.record_progress(
                TENANT, body.id, {"asking": {"id": "q-3", "kind": "mail_body", "text": "what?"}}
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            found = await uow.workflow_runs.waiting_on(TENANT, server="gmail", thread="t-3")
            assert found is not None and found.id == body.id

    async def test_clearing_a_wait_without_committing_does_not_clear_it(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The shape of a real defect, kept as a test rather than a memory.

        `_settle_the_wait` saved the cleared row and never committed, so the
        clear was rolled back on the way out and the run went on naming a
        conversation it had finished with -- for seven days, swallowing every
        reply to that thread. Every unit test passed: `FakeUnitOfWork` does not
        require a commit, so it agreed with the code rather than with the
        store. Measured on the deployment 2026-09-18.
        """
        run = _run(
            device_id="dev_f",
            outcome="held",
            awaiting={"server": "gmail", "thread": "t-6", "until": "2099-01-01T00:00:00+00:00"},
        )
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        # Saved and NOT committed, which is what the defect did.
        async with SqlUnitOfWork(session_factory) as uow:
            found = await uow.workflow_runs.get(TENANT, run.id)
            assert found is not None
            found.awaiting = None
            await uow.workflow_runs.save(found)

        async with SqlUnitOfWork(session_factory) as uow:
            still = await uow.workflow_runs.get(TENANT, run.id)
            assert still is not None
            assert still.awaiting is not None, (
                "an uncommitted clear appeared to stick, so this test cannot "
                "catch the defect it was written for"
            )

        # And committed, which is what it does now.
        async with SqlUnitOfWork(session_factory) as uow:
            found = await uow.workflow_runs.get(TENANT, run.id)
            assert found is not None
            found.awaiting = None
            await uow.workflow_runs.save(found)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            gone = await uow.workflow_runs.get(TENANT, run.id)
            assert gone is not None and gone.awaiting is None
            assert await uow.workflow_runs.waiting_on(TENANT, server="gmail", thread="t-6") is None

    async def test_the_settling_itself_survives_the_unit_of_work_closing(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The call site, not just the mechanism.

        The test above proves an uncommitted write rolls back. It does not stop
        anybody removing the commit from `_settle_the_wait` again, because the
        unit tests cannot see the difference -- `FakeUnitOfWork` does not
        require one. So this drives the real method against real Postgres and
        reads the row back in a session of its own.
        """
        from sro.application.execution.approvals import Approvals
        from sro.application.execution.one_time_secrets import OneTimeSecrets
        from sro.application.execution.stops import Stops
        from sro.application.execution.workflow_runs import StartWorkflowRun

        run = _run(
            device_id="dev_g",
            outcome="held",
            awaiting={"server": "gmail", "thread": "t-5", "until": "2099-01-01T00:00:00+00:00"},
        )
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        starter = StartWorkflowRun(
            SqlUnitOfWork(session_factory),
            channel=None,
            asker=None,
            clock=_Clock(),
            cap_usd=1.0,
            stops=Stops(),
            approvals=Approvals(),
            one_time_secrets=OneTimeSecrets(),
        )
        await starter._settle_the_wait(
            RequestContext(tenant_id=TENANT, principal_id=PrincipalId("operator")), run
        )

        async with SqlUnitOfWork(session_factory) as uow:
            settled = await uow.workflow_runs.get(TENANT, run.id)
            assert settled is not None
            assert settled.awaiting is None, "the clear did not survive the unit of work closing"

    async def test_a_run_that_stopped_waiting_is_found_by_nobody(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Cleared rather than left to expire: seven days of a finished run
        claiming every reply to its own thread is seven days of the next
        request on it being swallowed by the last one."""
        run = _run(
            device_id="dev_d",
            outcome="held",
            awaiting={"server": "gmail", "thread": "t-7", "until": "2099-01-01T00:00:00+00:00"},
        )
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        run.awaiting = None
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflow_runs.waiting_on(TENANT, server="gmail", thread="t-7") is None
            saved = await uow.workflow_runs.get(TENANT, run.id)
            assert saved is not None and saved.awaiting is None

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


class TestProgressWrittenOnlyByRecordProgress:
    """§7.3: "a write already recorded as done is never sent again, even when
    Temporal retries." `save` upserts a whole in-memory copy of a run, and an
    API path (a mail reply, a stop, a close) routinely loads a run, does
    something unrelated to `progress`, and saves it back -- possibly after a
    worker has since marked a later step `done` on the same row. If `save`
    ever wrote `progress`, that stale copy would rewind it, and a retried
    activity would resend a write already made."""

    async def test_a_stale_whole_row_save_does_not_roll_progress_back(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        run = _run(executor="steel", device_id="")

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        # The worker's view: loaded once, then it marks step 0 done.
        async with SqlUnitOfWork(session_factory) as uow:
            worker_copy = await uow.workflow_runs.get(TENANT, run.id)
            assert worker_copy is not None
            recorded = await uow.workflow_runs.record_progress(
                TENANT, run.id, {"step": 1, "marks": {"0": {"wrote": "done"}}}
            )
            await uow.commit()

        assert recorded is True

        # A concurrent API path's view: loaded BEFORE the worker's write above,
        # touches something that has nothing to do with progress, and saves
        # its now-stale whole copy back.
        async with SqlUnitOfWork(session_factory) as uow:
            stale_copy = await uow.workflow_runs.get(TENANT, run.id)
            assert stale_copy is not None
            stale_copy.watched = True
            await uow.workflow_runs.save(stale_copy)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflow_runs.get(TENANT, run.id)

        assert back is not None
        assert back.watched is True, "the stale save's own change still landed"
        assert back.progress == {
            "step": 1,
            "marks": {"0": {"wrote": "done"}},
        }, "the worker's done mark must survive a stale whole-row save"

    async def test_the_first_save_still_writes_the_initial_progress(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """`record_progress` is the only path that CHANGES progress -- the
        first `save` still has to write whatever progress the caller starts
        the row with, since nothing else has inserted the row yet."""
        run = _run(executor="steel", device_id="", progress={"step": 0, "lease": "lse_1"})

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflow_runs.get(TENANT, run.id)

        assert back is not None and back.progress == {"step": 0, "lease": "lse_1"}

    async def test_record_progress_writes_only_over_the_progress_it_was_given(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A compare-and-set: of two attempts that loaded the same progress,
        the second to write finds it changed and writes nothing."""
        loaded = {"step": 0, "marks": {"0": {"lane": "", "verdict": "", "wrote": ""}}}
        run = _run(executor="steel", device_id="", progress=loaded)
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        outcomes = []
        for lane in ("ui", "sight"):
            sending = {"step": 0, "marks": {"0": {"lane": lane, "wrote": "sending"}}}
            async with SqlUnitOfWork(session_factory) as uow:
                outcomes.append(
                    await uow.workflow_runs.record_progress(TENANT, run.id, sending, was=loaded)
                )
                await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflow_runs.get(TENANT, run.id)
        assert outcomes == [True, False]
        assert back is not None and back.progress["marks"] == {
            "0": {"lane": "ui", "wrote": "sending"}
        }

    async def test_record_progress_returns_false_for_an_unknown_run(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A worker that has lost its run must find that out, not believe a
        no-op mark is durable."""
        async with SqlUnitOfWork(session_factory) as uow:
            recorded = await uow.workflow_runs.record_progress(
                TENANT, "run_no_such_run", {"step": 1}
            )
            await uow.commit()

        assert recorded is False

    async def test_record_progress_returns_false_for_the_wrong_tenant(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        run = _run(executor="steel", device_id="")

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(run)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            recorded = await uow.workflow_runs.record_progress(OTHER_TENANT, run.id, {"step": 1})
            await uow.commit()

        assert recorded is False

        async with SqlUnitOfWork(session_factory) as uow:
            untouched = await uow.workflow_runs.get(TENANT, run.id)

        assert untouched is not None and untouched.progress == {}


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

    async def test_a_steel_run_is_never_an_orphan(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A Steel run lives in the worker, not the API process it starts
        beside -- an API restart is not its process dying, so the startup
        sweep must never fail one."""
        extension = _run(id="run_extension", steps=[RunStep(order=0, says="s", verdict="held")])
        steel = _run(id="run_steel", device_id="", executor="steel")

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(extension)
            await uow.workflow_runs.save(steel)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            swept = await uow.workflow_runs.fail_orphans("the rig restarted")
            await uow.commit()

        assert swept == 1

        async with SqlUnitOfWork(session_factory) as uow:
            failed = await uow.workflow_runs.get(TENANT, extension.id)
            untouched = await uow.workflow_runs.get(TENANT, steel.id)

        assert failed is not None and failed.outcome == "failed"
        assert untouched is not None and untouched.outcome == "running"


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


class TestOneRunningRunPerBrowser:
    """The index itself, asked of the database rather than of a race.

    `test_two_presses_at_once_do_not_both_get_the_browser` is the behaviour
    this backs, and its own docstring says what it cannot do: gathered presses
    are two coroutines on one loop, and whether the second one yields before
    the first commits is a scheduling question. Run inside the directory the
    caches are warm, press one finishes first, and `in_flight` answers on its
    own -- so `make check` stayed green with
    `uq_workflow_runs_one_running_per_device` deleted from the models.

    Two tests, because the index has two halves and losing either is silent:
    that Postgres refuses the second row, and that the object refusing it is
    UNIQUE and scoped to `outcome = 'running'`. An index that lost its
    predicate would refuse a browser its SECOND run ever; one that lost
    `unique` would refuse nothing and still pass a test that only checks the
    name.
    """

    async def test_postgres_refuses_a_second_running_row_for_one_browser(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(_run(id="run_first", outcome="running"))
            await uow.commit()

        with pytest.raises(Conflict) as refused:
            async with SqlUnitOfWork(session_factory) as uow:
                await uow.workflow_runs.save(_run(id="run_second", outcome="running"))
                await uow.commit()

        # The sentence a person reads, not just the violation: the repository
        # turns the index's refusal into the same answer the busy check gives,
        # naming the run that holds the browser.
        assert "run_first" in str(refused.value)

    async def test_a_browser_whose_run_has_ended_may_start_another(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The other half of the predicate, and the reason it is partial: a
        browser is free the moment its run is not `running`, and an index that
        forgot the `WHERE` would let a browser do one job, ever."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(_run(id="run_done", outcome="held"))
            await uow.workflow_runs.save(_run(id="run_also_done", outcome="failed"))
            await uow.workflow_runs.save(_run(id="run_now", outcome="running"))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflow_runs.in_flight(TENANT, DeviceId("dev_1")) == "run_now"

    async def test_another_browser_and_another_tenant_are_not_this_browser(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(_run(id="run_mine", outcome="running"))
            await uow.workflow_runs.save(
                _run(id="run_other_device", device_id="dev_2", outcome="running")
            )
            await uow.workflow_runs.save(
                _run(id="run_other_tenant", tenant=OTHER_TENANT.value, outcome="running")
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflow_runs.in_flight(TENANT, DeviceId("dev_1")) == "run_mine"
            assert (
                await uow.workflow_runs.in_flight(TENANT, DeviceId("dev_2")) == "run_other_device"
            )

    async def test_the_index_is_unique_and_only_over_running_rows(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """What the object actually is, read back out of Postgres.

        `test_the_migrations_run` asserts this index's NAME. A name is not a
        constraint: an index that arrived without `unique`, or without the
        predicate, carries the same name and answers the same assertion.
        """
        async with session_factory() as session:
            said = (
                await session.execute(
                    text(
                        "select indexdef from pg_indexes "
                        "where indexname = 'uq_workflow_runs_one_running_per_device'"
                    )
                )
            ).scalar_one()

        assert "CREATE UNIQUE INDEX" in said, said
        assert "tenant_id" in said and "device_id" in said, said
        assert "outcome" in said and "'running'" in said and "WHERE" in said, said
        assert "executor" in said and "'extension'" in said, said

    async def test_two_steel_runs_name_no_device_and_never_collide(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A Steel run has its own browser, not the operator's -- the index is
        narrowed to `executor = 'extension'` for exactly this: two Steel runs
        of one tenant, both `running`, both `device_id = ""`, save without a
        conflict and read back with their own progress."""
        first = _run(
            id="run_steel_first",
            device_id="",
            executor="steel",
            progress={"step": 1, "lease": "lse_1"},
        )
        second = _run(
            id="run_steel_second",
            device_id="",
            executor="steel",
            progress={"step": 2, "lease": "lse_2"},
        )

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(first)
            await uow.workflow_runs.save(second)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back_first = await uow.workflow_runs.get(TENANT, first.id)
            back_second = await uow.workflow_runs.get(TENANT, second.id)

        assert back_first is not None and back_first.outcome == "running"
        assert back_first.executor == "steel" and back_first.progress == {
            "step": 1,
            "lease": "lse_1",
        }
        assert back_second is not None and back_second.outcome == "running"
        assert back_second.executor == "steel" and back_second.progress == {
            "step": 2,
            "lease": "lse_2",
        }


class TestExecutorIsConstrained:
    """I1: the one-device rule is written three ways -- the index, the
    startup sweep, and `in_flight` -- and all three read `executor` as a
    bare string. A CHECK constraint is the one place a mistyped value
    (`"Extension"`, `""`) cannot slip past all three at once."""

    async def test_postgres_refuses_an_unknown_executor_value(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        bad = _run(id="run_bad_executor", executor="Extension")

        with pytest.raises(IntegrityError):
            async with SqlUnitOfWork(session_factory) as uow:
                await uow.workflow_runs.save(bad)
                await uow.commit()

    async def test_in_flight_ignores_a_steel_run_even_if_it_names_a_device(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        odd = _run(id="run_steel_odd_device", device_id="dev_1", executor="steel")

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(odd)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflow_runs.in_flight(TENANT, DeviceId("dev_1")) is None


class TestOneSkillRunPerBrowser:
    """The same rule for the older path, which had none of it.

    `workflow_runs` has had `uq_workflow_runs_one_running_per_device` since
    0043; `runs` had `runs_pkey` and two plain indexes. Two triggers firing two
    skills at one browser in the same minute both started, and their clicks
    interleaved in one window -- the corrupted form against a live warehouse
    that 0043's own docstring is about.
    """

    async def test_postgres_refuses_a_second_unfinished_skill_run(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.runs.add(_skill_run("run_first"))
            await uow.commit()

        with pytest.raises(IntegrityError):
            async with SqlUnitOfWork(session_factory) as uow:
                await uow.runs.add(_skill_run("run_second"))
                await uow.commit()

    async def test_a_browser_whose_skill_run_has_ended_may_start_another(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.runs.add(
                _skill_run("run_done", ended_at=datetime(2026, 9, 5, 11, tzinfo=UTC))
            )
            await uow.runs.add(_skill_run("run_now"))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.runs.in_flight(TENANT, DeviceId("dev_1")) == "run_now"

    async def test_a_run_in_a_browser_of_ours_names_no_device_and_never_collides(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A Steel run has its own browser. Postgres does not collide NULLs in
        a unique index, which is the answer wanted rather than an exception to
        write down -- and is why the index is on `device_id` as it stands."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.runs.add(_skill_run("run_steel_1", device_id=None))
            await uow.runs.add(_skill_run("run_steel_2", device_id=None))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.runs.in_flight(TENANT, DeviceId("dev_1")) is None
