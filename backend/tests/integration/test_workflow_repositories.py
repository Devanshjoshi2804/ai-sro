"""Workflows, the steps they cite, and what they earned, against real Postgres.

The rules under test are the rig's own -- ``rig/workflows.py``, ``rig/effects.py``,
the ``passes`` insert and the ``rekey`` update in ``rig/mine.py``, the
``workflow_stale`` insert and delete in ``rig/runner.py``, and the stale count in
``rig/api.py``. They were SQLite there and are SQL here, and a rule that changed
on the way across is the failure this port exists to avoid.

The first four names come from ``new_agent_arch/tests/test_workflows.py``. The
rest are the effects and stale rules, which plan 1 ported as pure rules in
``sro.domain.execution.belts`` and which nothing had yet proven against a store.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.observation.mining_pass import mine
from sro.domain.execution.belts import RunProof, earned_from
from sro.domain.execution.workflow_run import RunStep, WorkflowRun, new_run_id
from sro.domain.observation.mining import MiningPass
from sro.domain.shared.errors import Conflict, NotFound
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow, new_workflow_id
from sro.infrastructure.db.models import WorkflowEffectRow
from sro.infrastructure.db.repositories import SqlUnitOfWork
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import FakeAsker

FOUND_BY = "pas_abcdef"

TENANT = TenantId("acme")
OTHER_TENANT = TenantId("other-corp")


def _workflow(**overrides: Any) -> Workflow:
    fields: dict[str, Any] = {
        "id": new_workflow_id(),
        "tenant": TENANT.value,
        "title": "create a supplier",
        "narrative": "the operator created a supplier and set its status",
        "systems": ["https://wms.example", "https://sap.example"],
        "steps": [
            Step(
                order=0,
                says="create the supplier",
                system="https://wms.example",
                cites=["ges_1", "ges_2"],
                parameters=["supplier_name"],
            ),
            Step(
                order=1,
                says="set the status",
                system="https://sap.example",
                cites=["ges_3"],
                parameters=[],
            ),
        ],
        "parameters": [{"name": "supplier_name", "seen_values": ["TestYonder2"]}],
        "shape_key": [["https://wms.example", "clientCode", "type"]],
        "same_as": None,
        "unproven": ["ges_9"],
        "pass_id": "pas_1",
    }
    fields.update(overrides)
    return Workflow(**fields)


def _run(workflow_id: str, **overrides: Any) -> WorkflowRun:
    fields: dict[str, Any] = {
        "id": new_run_id(),
        "tenant": TENANT.value,
        "workflow_id": workflow_id,
        "device_id": "dev_1",
        "values": {"workArea": "THIRD"},
        "started_by": "form",
        "live": True,
        "allow_focus": False,
        "started_at": "2026-09-05T10:00:00+00:00",
        "outcome": "held",
    }
    fields.update(overrides)
    return WorkflowRun(**fields)


def _wrote(order: int) -> RunStep:
    """A step the runner marked as having written.

    ``wrote`` is the one fact ``proofs`` needs and cannot recompute: SQL cannot
    ask ``writes()``, and the evidence a later reader would have to ask it about
    may have been re-mined by then.
    """
    return RunStep(
        order=order,
        says="save",
        verdict="held",
        verdict_by="status",
        result={"ok": True, "status": 200, "wrote": True},
    )


class TestWorkflows:
    async def test_a_workflow_survives_a_round_trip(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        workflow = _workflow()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflows.known(TENANT)
            one = await uow.workflows.get(TENANT, workflow.id)

        assert len(back) == 1
        assert back[0] == workflow
        assert back[0].title == "create a supplier"
        assert [step.says for step in back[0].steps] == ["create the supplier", "set the status"]
        assert back[0].steps[0].cites == ["ges_1", "ges_2"]
        assert back[0].systems == ["https://wms.example", "https://sap.example"]
        assert one == workflow

    async def test_a_workflow_names_the_pass_that_found_it(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The umbrella pass is the most expensive call in the system, and it is
        the pass that is billed. A workflow carries the id of the pass rather
        than a copy of its cost -- three workflows out of one $0.04 call summed
        to $0.12, and the better the pass did the worse the figure got."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(_workflow(pass_id=FOUND_BY))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = (await uow.workflows.known(TENANT))[0]

        assert back.pass_id == FOUND_BY

    async def test_another_tenants_workflows_are_not_returned(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        mine = _workflow(tenant=TENANT.value)
        theirs = _workflow(tenant=OTHER_TENANT.value)

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(mine)
            await uow.workflows.save(theirs)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert len(await uow.workflows.known(TENANT)) == 1
            assert len(await uow.workflows.known(OTHER_TENANT)) == 1
            with pytest.raises(NotFound):
                await uow.workflows.get(TENANT, theirs.id)

    async def test_saving_the_same_workflow_twice_keeps_one(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Steps are replaced rather than appended: identity resolution re-saves
        a workflow it has merged evidence into, and the second save must not
        double its steps."""
        workflow = _workflow()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            await uow.workflows.save(workflow)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflows.known(TENANT)

        assert len(back) == 1
        assert len(back[0].steps) == 2

    async def test_known_is_oldest_first_and_a_re_saved_workflow_is_the_newest(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The order is load-bearing, not cosmetic: ``resolve`` breaks a tie
        with a strict ``>``, so the first workflow at the top score wins and
        this order decides which job a proposal is resolved into.

        Re-saving rewrites ``created_at``, which is what INSERT OR REPLACE did
        in the rig and is why a merged workflow moves to the end.
        """
        first, second = _workflow(), _workflow()

        for workflow in (first, second, first):
            async with SqlUnitOfWork(session_factory) as uow:
                await uow.workflows.save(workflow)
                await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflows.known(TENANT)

        assert [row.id for row in back] == [second.id, first.id]

    async def test_a_workflow_that_lost_a_step_loses_it_in_the_store_too(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        workflow = _workflow()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            workflow.steps = workflow.steps[:1]
            await uow.workflows.save(workflow)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflows.get(TENANT, workflow.id)

        assert [step.order for step in back.steps] == [0]

    async def test_rekeying_replaces_the_shape_the_miner_resolves_against(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """When the rule that makes a key changes, keys mined before it no
        longer match keys mined after, and a job the rig already holds could be
        proposed again as a new one."""
        workflow = _workflow()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.rekey(
                TENANT, workflow.id, (("https://sap.example", "status", "click"),)
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflows.get(TENANT, workflow.id)

        assert back.shape_key == [["https://sap.example", "status", "click"]]

    async def test_a_workflow_nobody_saved_is_not_found(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            with pytest.raises(NotFound):
                await uow.workflows.get(TENANT, "wfl_nobody")


class TestMiningPasses:
    async def test_a_pass_records_what_it_cost_even_when_it_found_nothing(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """One row per reading of the day, written whether it found anything or
        not -- including when it was refused, which is the only record left of a
        call that cost money and returned nothing."""
        refused = MiningPass(
            id="pas_refused",
            tenant=TENANT.value,
            started_at="2026-09-05T09:00:00+00:00",
            in_tokens=4210,
            out_tokens=0,
            thought_tokens=0,
            cost_usd=0.0042,
            unpriced=False,
            proposed=0,
            kept=0,
            rejected=0,
            coverage=0.0,
            skew=0.0,
            lopsided=False,
            error="the model refused: RECITATION",
        )

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.add_pass(refused)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflows.passes(TENANT)

        assert back == (refused,)

    async def test_another_tenants_passes_are_not_returned_and_an_id_is_not_reused(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A pass id is minted per reading, so a second row under one id is one
        model call billed twice."""
        mine = MiningPass(
            id="pas_mine", tenant=TENANT.value, started_at="2026-09-05T09:00:00+00:00"
        )
        theirs = MiningPass(
            id="pas_theirs", tenant=OTHER_TENANT.value, started_at="2026-09-05T09:00:00+00:00"
        )

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.add_pass(mine)
            await uow.workflows.add_pass(theirs)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflows.passes(TENANT) == (mine,)
            assert await uow.workflows.passes(OTHER_TENANT) == (theirs,)

        async with SqlUnitOfWork(session_factory) as uow:
            with pytest.raises(Conflict):
                await uow.workflows.add_pass(mine)


class TestEffects:
    async def test_an_effect_is_recorded_once_per_step_of_a_run(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """(workflow, run, step) is the key. A write rescued to the second rung
        verifies at the same step, and that is one effect, not two."""
        workflow = _workflow()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            for verified_by in ("status", "read"):
                await uow.workflows.record_effect(
                    workflow.id,
                    run_id="run_1",
                    ord_=1,
                    verified_by=verified_by,
                    at="2026-09-05T10:01:00+00:00",
                )
            await uow.workflows.record_effect(
                workflow.id,
                run_id="run_1",
                ord_=2,
                verified_by="status",
                at="2026-09-05T10:02:00+00:00",
            )
            await uow.commit()

        async with session_factory() as session:
            belts = (
                await session.execute(
                    select(WorkflowEffectRow.ord, WorkflowEffectRow.verified_by)
                    .where(WorkflowEffectRow.workflow_id == workflow.id)
                    .order_by(WorkflowEffectRow.ord)
                )
            ).all()

        # The second verify REPLACED the first rather than being dropped: a
        # count alone cannot tell ON CONFLICT DO UPDATE from DO NOTHING, and
        # the belt that last saw the state is the current answer about it.
        assert [tuple(row) for row in belts] == [(1, "read"), (2, "status")]

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflows.forget_effects(workflow.id) == 2
            await uow.commit()

    async def test_a_picture_is_never_an_effect(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A write counts only when the verifier decided ``held`` by state. A
        model reading a screenshot is not evidence anything was written."""
        workflow = _workflow()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            await uow.workflows.record_effect(
                workflow.id,
                run_id="run_1",
                ord_=1,
                verified_by="screen",
                at="2026-09-05T10:01:00+00:00",
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflows.forget_effects(workflow.id) == 0
            await uow.commit()

    async def test_a_failed_write_forgets_every_effect_the_workflow_had(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A failed write un-earns the job: the next runs ask again. Only this
        workflow's, though -- another job's earning is not this job's to spend."""
        mine = _workflow()
        other = _workflow()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(mine)
            await uow.workflows.save(other)
            for order in (1, 2, 3):
                await uow.workflows.record_effect(
                    mine.id,
                    run_id="run_1",
                    ord_=order,
                    verified_by="status",
                    at="2026-09-05T10:01:00+00:00",
                )
            await uow.workflows.record_effect(
                other.id,
                run_id="run_2",
                ord_=1,
                verified_by="read",
                at="2026-09-05T10:01:00+00:00",
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflows.forget_effects(mine.id) == 3
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflows.forget_effects(mine.id) == 0
            assert await uow.workflows.forget_effects(other.id) == 1
            await uow.commit()

    async def test_the_proof_a_run_leaves_is_read_back_as_the_domain_reads_it(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Three live held runs, each with every write verified by state, is what
        buys a job the right to write unasked. The repository assembles the
        proofs; ``earned_from`` decides.

        The four runs here are the four cases the rule turns on: two that prove,
        one whose write nothing verified, and one that never wrote at all.
        """
        workflow = _workflow()
        # Distinct clocks: ``proofs`` comes back oldest first, and runs that
        # started at the same instant would be a tie this assertion cannot name.
        proving = [
            _run(
                workflow.id, started_at=f"2026-09-05T10:0{n}:00+00:00", steps=[_wrote(0), _wrote(1)]
            )
            for n in (0, 1)
        ]
        unverified = _run(workflow.id, started_at="2026-09-05T10:02:00+00:00", steps=[_wrote(0)])
        read_only = _run(
            workflow.id,
            started_at="2026-09-05T10:03:00+00:00",
            steps=[RunStep(order=0, says="look", verdict="held", verdict_by="read")],
        )
        # Not counted: not live, and a dry run sends no writes to verify.
        rehearsal = _run(
            workflow.id, started_at="2026-09-05T10:04:00+00:00", live=False, steps=[_wrote(0)]
        )
        # Not counted: it did not hold.
        stopped = _run(
            workflow.id,
            started_at="2026-09-05T10:05:00+00:00",
            outcome="stopped",
            steps=[_wrote(0)],
        )

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            for run in [*proving, unverified, read_only, rehearsal, stopped]:
                await uow.workflow_runs.save(run)
                for step in run.steps:
                    if step.result and step.result.get("wrote") and run is not unverified:
                        await uow.workflows.record_effect(
                            workflow.id,
                            run_id=run.id,
                            ord_=step.order,
                            verified_by="status",
                            at="2026-09-05T10:01:00+00:00",
                        )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            proofs = await uow.workflows.proofs(TENANT, workflow.id)

        assert proofs == (
            RunProof(run_id=proving[0].id, wrote=frozenset({0, 1}), verified=frozenset({0, 1})),
            RunProof(run_id=proving[1].id, wrote=frozenset({0, 1}), verified=frozenset({0, 1})),
            RunProof(run_id=unverified.id, wrote=frozenset({0}), verified=frozenset()),
            RunProof(run_id=read_only.id, wrote=frozenset(), verified=frozenset()),
        )
        assert not earned_from(proofs)

        # The third proving run is the one that earns it.
        third = _run(
            workflow.id, started_at="2026-09-05T10:06:00+00:00", steps=[_wrote(0), _wrote(1)]
        )
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(third)
            for order in (0, 1):
                await uow.workflows.record_effect(
                    workflow.id,
                    run_id=third.id,
                    ord_=order,
                    verified_by="read",
                    at="2026-09-05T10:03:00+00:00",
                )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert earned_from(await uow.workflows.proofs(TENANT, workflow.id))
            # Another tenant asking about the same id is asking about nothing.
            assert await uow.workflows.proofs(OTHER_TENANT, workflow.id) == ()


class TestStaleSteps:
    async def test_a_step_only_the_weakest_rung_found_is_marked_stale_once(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """One row per step, so a job run every morning reports its weak step
        once rather than daily."""
        workflow = _workflow()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            for at in ("2026-09-05T10:00:00+00:00", "2026-09-06T10:00:00+00:00"):
                await uow.workflows.mark_stale(workflow.id, 1, matched_by="css_path", noticed_at=at)
            await uow.workflows.mark_stale(
                workflow.id, 0, matched_by=None, noticed_at="2026-09-06T10:00:00+00:00"
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflows.stale_count(workflow.id) == 2

    async def test_a_step_that_matched_properly_again_is_not_stale_any_more(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The page is not moving under it after all, and a warning that never
        clears is a warning nobody reads."""
        workflow = _workflow()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            await uow.workflows.mark_stale(
                workflow.id, 1, matched_by="css_path", noticed_at="2026-09-05T10:00:00+00:00"
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.clear_stale(workflow.id, 1)
            # Clearing a step that was never weak is not an error.
            await uow.workflows.clear_stale(workflow.id, 7)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflows.stale_count(workflow.id) == 0


class TestTheMiningPass:
    """The one rule of `mine` that only a real session can prove.

    Everything else about the pass is arithmetic over fakes in
    `tests/unit/application/rig/test_mine.py`. This is the half no fake can
    answer: what a store does to a transaction whose statement failed, and
    whether the bill the pass writes in its `finally` survives it.
    """

    async def test_the_bill_is_written_on_a_session_the_save_killed(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A pass whose workflow will not go into the store is still a pass
        that was billed.

        `same_as` is `varchar(64)` and comes straight off the model answer, so
        a model that names a job in a hundred characters is an ordinary
        statement error rather than a contrived one. Postgres then refuses
        every further statement on the transaction -- so before the
        rollback-and-retry this probe read `passes: 0, workflows: 0`, with a
        DBAPIError in place of the error that caused it, and the only record
        of a paid-for call was gone.

        The rig never met this: its `store.execute` opened a connection per
        statement, so each save was its own committed transaction. One session
        is this port's shape.
        """
        gestures = _gestures(TENANT.value)
        proposal = {
            "title": "create a work operation",
            "narrative": "n",
            "systems": [gestures[0].system],
            # Two steps, because `validate` refuses anything shorter than
            # `identity.K_MIN_SHARED_STEPS` and this probe needs the workflow
            # to reach the SAVE, where the oversized `same_as` kills the
            # statement. Both cite the same gesture, so nothing else moves.
            "steps": [
                {
                    "order": 0,
                    "cites": [gestures[0].id],
                    "says": "do it",
                    "system": gestures[0].system,
                },
                {
                    "order": 1,
                    "cites": [gestures[0].id],
                    "says": "save it",
                    "system": gestures[0].system,
                },
            ],
            # Longer than the column, which is what kills the statement.
            "same_as": "wfl_" + "0" * 100,
        }
        asker = FakeAsker(Answer(data={"workflows": [proposal]}, cost_usd=0.04))

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.add_gestures(tuple(gestures))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            with pytest.raises(DBAPIError):
                await mine(
                    uow,
                    tenant_id=TENANT,
                    asker=asker,
                    model="gemini-3.1-pro",
                    now=datetime(2025, 2, 11, 23, tzinfo=UTC),
                    cap_usd=100.0,
                )

        async with SqlUnitOfWork(session_factory) as uow:
            billed = await uow.workflows.passes(TENANT)
            kept = await uow.workflows.known(TENANT)

        assert [one.cost_usd for one in billed] == [0.04], "the call was billed; the row proves it"
        assert billed[0].proposed == 1
        # Postgres discarded them when the statement failed. Nothing here can
        # keep them, and the bill is what must not go with them.
        assert kept == ()
