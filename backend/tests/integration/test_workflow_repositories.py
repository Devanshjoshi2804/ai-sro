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

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from sro.application.context import RequestContext
from sro.application.observation.mining_pass import (
    _grow,
    _healed,
    fill_in_passwords,
    learn_parameters,
    mine,
)
from sro.application.runtime.teach import Teach
from sro.domain.execution.belts import RunProof, earned_from
from sro.domain.execution.compose import Composed, with_field
from sro.domain.execution.lanes import Broken, Lane, StepResult
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.execution.workflow_run import (
    RunStep,
    WorkflowRun,
    new_run_id,
    pin,
)
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.mining import MiningPass
from sro.domain.shared.errors import Conflict, NotFound
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow, new_workflow_id
from sro.infrastructure.db import workflows as workflows_module
from sro.infrastructure.db.locks import PostgresAccountLocks
from sro.infrastructure.db.models import WorkflowEffectRow
from sro.infrastructure.db.repositories import SqlUnitOfWork
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import FakeAccountLocks, FakeAsker, FakeClock

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

    async def test_a_job_that_signs_in_is_read_back_as_one(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Decided once by the mining pass and read by every run after it, so
        it has to survive the store -- and a re-save must be able to clear it
        when the healing pass reads the evidence differently. A job nobody has
        judged reads back undecided (None), never as decided."""
        workflow = _workflow(signs_in=True)
        ordinary = _workflow()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            await uow.workflows.save(ordinary)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert (await uow.workflows.get(TENANT, workflow.id)).signs_in is True
            assert (await uow.workflows.get(TENANT, ordinary.id)).signs_in is None
            workflow.signs_in = False
            await uow.workflows.save(workflow)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert (await uow.workflows.get(TENANT, workflow.id)).signs_in is False

    async def test_a_retired_job_stays_retired_and_its_evidence_stays_placed(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Retired is gone from everything that offers or runs a job -- the
        known list and a lookup by id -- and it survives a re-save of the same
        row. Its citations are still placed, so its gestures are never mined
        into a fresh copy of it."""
        retired = _workflow()
        kept = _workflow(
            steps=[Step(order=0, says="x", system="https://wms.example", cites=["ges_9"])]
        )

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(retired)
            await uow.workflows.save(kept)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.retire(TENANT, retired.id, at=datetime(2026, 9, 23, tzinfo=UTC))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert [one.id for one in await uow.workflows.known(TENANT)] == [kept.id]
            with pytest.raises(NotFound):
                await uow.workflows.get(TENANT, retired.id)
            assert await uow.workflows.placed(TENANT) == {"ges_1", "ges_2", "ges_3", "ges_9"}
            assert await uow.workflows.placed(OTHER_TENANT) == frozenset()
            await uow.workflows.save(retired)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert [one.id for one in await uow.workflows.known(TENANT)] == [kept.id]

    async def test_a_doing_folded_into_a_job_stays_placed(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A second doing recognised as a stored job is not a row of its own,
        and a growth replaces the steps that cited the first. Both doings stay
        placed, once each, for the tenant that did them and no other."""
        workflow = _workflow()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            await uow.workflows.place(TENANT, workflow.id, ("ges_7", "ges_8"))
            await uow.workflows.place(TENANT, workflow.id, ("ges_8", "ges_9"))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflows.placed(TENANT) == {
                "ges_1",
                "ges_2",
                "ges_3",
                "ges_7",
                "ges_8",
                "ges_9",
            }
            assert await uow.workflows.placed(OTHER_TENANT) == frozenset()

    async def test_only_the_tenants_own_job_can_be_retired(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        workflow = _workflow()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            with pytest.raises(NotFound):
                await uow.workflows.retire(OTHER_TENANT, workflow.id, at=datetime.now(tz=UTC))
            with pytest.raises(NotFound):
                await uow.workflows.retire(TENANT, "wfl_nobody", at=datetime.now(tz=UTC))

        async with SqlUnitOfWork(session_factory) as uow:
            assert [one.id for one in await uow.workflows.known(TENANT)] == [workflow.id]

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

    async def test_known_is_oldest_first_and_a_re_saved_workflow_keeps_its_place(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The order is load-bearing, not cosmetic: ``resolve`` breaks a tie
        with a strict ``>``, so the first workflow at the top score wins and
        this order decides which job a proposal is resolved into.

        A re-save keeps ``created_at``: a job's creation time never changes,
        so a merge or a learnt parameter does not move it.
        """
        first, second = _workflow(), _workflow()

        for workflow in (first, second, first):
            async with SqlUnitOfWork(session_factory) as uow:
                await uow.workflows.save(workflow)
                await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflows.known(TENANT)

        assert [row.id for row in back] == [first.id, second.id]

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

    async def test_a_job_that_grows_takes_its_learning_with_it(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Against real Postgres because the primary key is the point.

        `workflow_learned`, `workflow_stale` and `workflow_learned_history`
        are keyed `(workflow_id, ord)`, so a growth that renumbered step 1 to
        step 2 while step 2 still existed would collide on the key -- which is
        why the rows are read, deleted and reinserted rather than updated.

        A past run's own record is deliberately NOT moved: `run_steps` and
        `effects` are a log of what happened when the job had the shape it had
        then, and `proofs` compares those two with each other and never with
        the job. That is what keeps a growth from costing a job the autonomy
        it earned.
        """
        workflow = _workflow()
        workflow.steps = [
            Step(order=0, says="first", system=None, cites=["g0"]),
            Step(order=1, says="second", system=None, cites=["g1"]),
        ]

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            await uow.workflows.remember_locator(
                workflow.id,
                LearnedStep(ord=1, strategy="css", query="#save", found_by="sight"),
                by_run="run_1",
            )
            await uow.workflows.mark_stale(
                workflow.id, 1, matched_by="text", noticed_at="2026-09-21T10:00:00+00:00"
            )
            await uow.workflows.break_lane(
                TenantId("acme"),
                workflow.id,
                Broken(1, Lane.API, "fp"),
                cites="g1",
                at=datetime(2026, 9, 21, tzinfo=UTC),
            )
            await uow.commit()

        # It grows: what was step 1 is now step 2, with a new step between.
        async with SqlUnitOfWork(session_factory) as uow:
            grown = await uow.workflows.get(TenantId("acme"), workflow.id)
            grown.steps = [
                Step(order=0, says="first", system=None, cites=["g0"]),
                Step(order=1, says="the one in between", system=None, cites=["g2"]),
                Step(order=2, says="second", system=None, cites=["g1"]),
            ]
            await uow.workflows.grew(grown, moved={0: 0, 1: 2})
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            learnt = await uow.workflows.learned_for(workflow.id)
            assert [one.ord for one in learnt] == [2], (
                "the locator stayed on a step that is now somebody else's"
            )
            assert learnt[0].query == "#save"
            assert await uow.workflows.stale_count(workflow.id) == 1
            assert await uow.workflows.broken_for(
                TenantId("acme"), workflow.id, {2: "g1"}, now=datetime(2026, 9, 21, tzinfo=UTC)
            ) == (Broken(2, Lane.API, "fp"),), (
                "a lane known broken stayed on a step that is now somebody else's"
            )

    async def test_a_step_left_behind_takes_its_learning_with_it(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A locator for a step nobody performs is one nobody can check."""
        workflow = _workflow()
        workflow.steps = [Step(order=0, says="first", system=None, cites=["g0"])]

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            await uow.workflows.remember_locator(
                workflow.id,
                LearnedStep(ord=0, strategy="css", query="#gone", found_by="sight"),
                by_run="run_1",
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            grown = await uow.workflows.get(TenantId("acme"), workflow.id)
            grown.steps = [Step(order=0, says="something else", system=None, cites=["g9"])]
            await uow.workflows.grew(grown, moved={})
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflows.learned_for(workflow.id) == ()

    async def test_a_deployment_learns_the_endpoint_it_watched_succeed(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The other ledger, and the one a tenant can add to.

        `knowledge-base/index/write-endpoints.json` is a research project's
        file edited by hand between sessions, so a deployment that had watched
        its own write succeed could not say so -- and `plan_step` went on
        refusing to replay it. Against real Postgres because the gate and the
        idempotence both live in the statement.
        """
        async with SqlUnitOfWork(session_factory) as uow:
            for run in ("run_1", "run_2"):
                await uow.workflows.remember_write(
                    TenantId("acme"),
                    method="delete",
                    path_pattern="/data/WM/wm/customerTypes/{id}",
                    origin="https://wms.example",
                    run_id=run,
                    workflow_id="wfl_1",
                    verified_by="status",
                    at="2026-09-21T10:00:00+00:00",
                )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            learnt = await uow.workflows.learned_writes(TenantId("acme"))
            # Upper-cased on the way in, because the ledger matches that way.
            assert learnt == (
                VerifiedWrite(method="DELETE", path_pattern="/data/WM/wm/customerTypes/{id}"),
            ), "one endpoint proved twice is one row"
            assert await uow.workflows.learned_writes(TenantId("someone-else")) == ()

    async def test_a_picture_never_earns_an_endpoint_in_the_store(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The gate is kept by the statement, not by the caller -- and this is
        the half a fake cannot prove, because the fake keeps its own copy of
        it. Removing the gate from the repository left every unit test green.
        """
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.remember_write(
                TenantId("acme"),
                method="POST",
                path_pattern="/data/WM/wm/customerTypes",
                origin="https://wms.example",
                run_id="run_1",
                workflow_id="wfl_1",
                verified_by="screen",
                at="2026-09-21T10:00:00+00:00",
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.workflows.learned_writes(TenantId("acme")) == ()

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


FAILS = "the step Postgres refuses"


def _a_step_postgres_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    """A step whose insert fails on the server. `workflow_from` refuses what a
    model could send to make one (control characters, orders past int32), so
    the failure is planted below the domain: the row's key outgrows its column."""
    real = workflows_module._step_values

    def refused(workflow_id: str, step: Step) -> dict[str, Any]:
        values = real(workflow_id, step)
        return {**values, "workflow_id": "w" * 65} if step.says == FAILS else values

    monkeypatch.setattr(workflows_module, "_step_values", refused)


class TestWhatAPassHasMined:
    """What a pass read is recorded in the same transaction as what it kept,
    under the tenant's mining lock -- proved against the real lock and store."""

    async def test_a_re_saved_job_keeps_a_column_nothing_maps_any_more(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """`workflows.same_as` stays in the schema with nothing writing it
        (GC 17). A re-save replaces what it supplies, and only that."""
        job = _workflow()
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(job)
            await uow.commit()
        async with session_factory() as session:
            await session.execute(text("UPDATE workflows SET same_as = 'wfl_older'"))
            await session.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(replace(job, title="renamed"))
            await uow.commit()

        async with session_factory() as session:
            kept = await session.scalar(text("SELECT same_as FROM workflows"))
        assert kept == "wfl_older"

    async def test_the_bill_is_written_on_a_session_the_save_killed(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A pass whose workflow will not go into the store is still a pass that
        was billed. Postgres refuses every further statement on a transaction
        whose statement failed, so without the rollback-and-retry in `_one_pass`'s
        `finally` the bill went with it. The statement is killed on the server:
        one step's row carries a key longer than its column allows."""
        _a_step_postgres_refuses(monkeypatch)
        gestures = _gestures(TENANT.value)
        proposal = {
            "title": "create a work operation",
            "narrative": "n",
            "systems": [gestures[0].system],
            "steps": [
                {"order": 0, "cites": [gestures[0].id], "says": "do it"},
                {"order": 1, "cites": [gestures[0].id], "says": FAILS},
            ],
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
                    locks=FakeAccountLocks(),
                    now=datetime(2025, 2, 11, 23, tzinfo=UTC),
                    cap_usd=100.0,
                )

        async with SqlUnitOfWork(session_factory) as uow:
            billed = await uow.workflows.passes(TENANT)
            kept = await uow.workflows.known(TENANT)
        assert [one.cost_usd for one in billed] == [0.04]
        assert billed[0].proposed == 1
        assert kept == ()

    async def test_a_job_whose_steps_fail_is_not_stored_and_the_job_before_it_is(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Saving one job is one savepoint. A step insert that fails takes that
        job's row back with it, and the pass's `finally` -- which commits the
        bill -- can then never commit a job without its steps. The job kept
        earlier in the same pass is untouched."""
        _a_step_postgres_refuses(monkeypatch)
        day = _gestures(TENANT.value)
        gestures = {g.action.kind: g for g in day}
        typed, picked = gestures["type"], gestures["select"]
        good = {
            "title": "create a work operation",
            "narrative": "n",
            "systems": [typed.system],
            "steps": [
                {"order": 0, "cites": [typed.id], "says": "type it"},
                {"order": 1, "cites": [typed.id], "says": "save it"},
            ],
        }
        bad = {
            "title": "pick a dock",
            "narrative": "n",
            "systems": [picked.system],
            "steps": [
                {"order": 0, "cites": [picked.id], "says": "pick it"},
                {"order": 1, "cites": [picked.id], "says": FAILS},
            ],
        }
        asker = FakeAsker(Answer(data={"workflows": [good, bad]}, cost_usd=0.04))
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.add_gestures(tuple(day))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            with pytest.raises(DBAPIError):
                await mine(
                    uow,
                    tenant_id=TENANT,
                    asker=asker,
                    locks=FakeAccountLocks(),
                    now=datetime(2025, 2, 11, 23, tzinfo=UTC),
                    cap_usd=100.0,
                )

        async with SqlUnitOfWork(session_factory) as uow:
            kept = await uow.workflows.known(TENANT)
            billed = await uow.workflows.passes(TENANT)
        async with session_factory() as session:
            rows = await session.scalar(text("SELECT count(*) FROM workflows"))
            steps = await session.scalar(text("SELECT count(*) FROM workflow_steps"))
        assert [one.title for one in kept] == ["create a work operation"]
        assert (rows, steps) == (1, len(kept[0].steps))
        assert [one.cost_usd for one in billed] == [0.04]

    async def test_two_passes_at_once_ask_the_model_once(
        self, session_factory: async_sessionmaker[AsyncSession], engine: AsyncEngine
    ) -> None:
        gestures = _gestures(TENANT.value)
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.add_gestures(tuple(gestures))
            await uow.commit()
        proposal = {
            "title": "create a work operation",
            "narrative": "n",
            "systems": [gestures[0].system],
            "steps": [
                {"order": 0, "cites": [gestures[0].id], "says": "do it"},
                {"order": 1, "cites": [gestures[0].id], "says": "save it"},
            ],
        }
        asker = FakeAsker(*[Answer(data={"workflows": [proposal]}, cost_usd=0.01)] * 2)
        locks = PostgresAccountLocks(engine)

        async def mines() -> None:
            async with SqlUnitOfWork(session_factory) as uow:
                await mine(
                    uow,
                    tenant_id=TENANT,
                    asker=asker,
                    locks=locks,
                    now=datetime(2025, 2, 11, 23, tzinfo=UTC),
                    cap_usd=100.0,
                )

        await asyncio.gather(mines(), mines())

        async with SqlUnitOfWork(session_factory) as uow:
            kept = await uow.workflows.known(TENANT)
            billed = await uow.workflows.passes(TENANT)
        assert len(asker.asked) == 1
        assert len(kept) == 1
        assert sorted(one.cost_usd for one in billed) == [0.0, 0.01]


class TestAStepNamesWhatItUses:
    async def test_the_edge_survives_a_round_trip(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A declaration nothing stores is a declaration nothing can act on."""
        workflow = _workflow()
        workflow.steps[1].uses = [workflow.steps[0].order]

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflows.get(TENANT, workflow.id)

        assert [step.uses for step in back.steps] == [[], [workflow.steps[0].order]]

    async def test_a_job_that_uses_nothing_reads_back_using_nothing(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Which is every job mined so far. An older row has no column at all,
        and a job that predates it used nothing -- what an absent one honestly
        means."""
        workflow = _workflow()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflows.get(TENANT, workflow.id)

        assert all(step.uses == [] for step in back.steps)

    async def test_a_steps_tab_survives_a_save(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        workflow = _workflow()
        workflow.steps[1].tab = "opened_from:main"

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(workflow)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflows.get(TENANT, workflow.id)

        assert [step.tab for step in back.steps] == ["main", "opened_from:main"]


class TestWhatAJobTaughtItself:
    """The history behind the learning, against the store that overwrites it.

    `workflow_learned` is one row per step and the last answer wins -- so this
    is exactly the rule a fake would get right by accident and the store would
    get wrong: the comparison has to happen BEFORE the upsert, because the
    upsert is what destroys the answer being compared against.
    """

    async def test_a_locator_that_moved_is_kept_with_what_it_replaced(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(_workflow())
            await uow.workflows.remember_locator(
                "wfl_1", LearnedStep(2, "component", "tabItem", "evidence"), by_run="run_a"
            )
            await uow.workflows.remember_locator(
                "wfl_1", LearnedStep(2, "css_path", "#a > b", "sight"), by_run="run_b"
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            changes = await uow.workflows.taught_itself("wfl_1")

        # Newest first, and both: the first is a job learning something it
        # never knew, and the second is a job changing its mind.
        assert [(one.was, one.now) for one in changes] == [
            ("component=tabItem", "css_path=#a > b"),
            ("", "component=tabItem"),
        ]
        assert [one.by_run for one in changes] == ["run_b", "run_a"]
        assert changes[0].found_by == "sight"

    async def test_a_sight_locator_keeps_its_frame_through_a_limit_and_loses_it_when_replaced(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        hops = '[{"index": 1, "url": "https://wms.example/frames/form"}]'
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(_workflow())
            await uow.workflows.remember_locator(
                "wfl_1", LearnedStep(2, "component", "#save", "sight", frame_path=hops)
            )
            await uow.workflows.remember_limit("wfl_1", 2, 40)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            kept = await uow.workflows.learned_for("wfl_1")
            await uow.workflows.remember_locator("wfl_1", LearnedStep(2, "text", "Save", "text"))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            replaced = await uow.workflows.learned_for("wfl_1")

        assert [(one.query, one.holds, one.frame_path) for one in kept] == [("#save", 40, hops)]
        assert [(one.query, one.frame_path) for one in replaced] == [("Save", None)]

    async def test_a_run_that_found_what_the_last_one_found_writes_nothing(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Four hundred rows saying "the same locator again" bury the four that
        matter."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(_workflow())
            for run in ("run_a", "run_b", "run_c"):
                await uow.workflows.remember_locator(
                    "wfl_1", LearnedStep(2, "component", "tabItem", "evidence"), by_run=run
                )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            changes = await uow.workflows.taught_itself("wfl_1")

        assert len(changes) == 1

    async def test_a_measured_limit_does_not_read_as_a_locator_being_erased(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A limit is learnt on a step whose locator matched perfectly well.
        Comparing a bare limit against a step that has a locator would write a
        change saying the locator had been thrown away."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(_workflow())
            await uow.workflows.remember_locator(
                "wfl_1", LearnedStep(2, "component", "tabItem", "evidence"), by_run="run_a"
            )
            await uow.workflows.remember_limit("wfl_1", 2, 4, by_run="run_b")
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            changes = await uow.workflows.taught_itself("wfl_1")
            learned = await uow.workflows.learned_for("wfl_1")

        assert [(one.about, one.was, one.now) for one in changes] == [
            ("holds", "", "4"),
            ("locator", "", "component=tabItem"),
        ]
        # And the locator is still there, which is the store's own rule: each
        # writes only its own columns.
        assert learned[0].query == "tabItem"
        assert learned[0].holds == 4

    async def test_another_job_history_is_not_this_one(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(_workflow())
            await uow.workflows.remember_locator(
                "wfl_1", LearnedStep(2, "component", "a", "evidence"), by_run="run_a"
            )
            await uow.workflows.remember_locator(
                "wfl_2", LearnedStep(2, "component", "b", "evidence"), by_run="run_b"
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert len(await uow.workflows.taught_itself("wfl_1")) == 1


class TestARunKeepsItsVersion:
    """X11: a grow renumbers the job's steps and what the job learned by step
    number. Every writer that renumbers, and every reader or teacher that
    trusts the numbering, holds the job's row lock; each test here holds a
    grow open on the row and runs one of them against it, and goes red if
    that one does not take the lock."""

    async def test_two_runs_learning_on_one_version_grow_the_job_once(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        job = _workflow()
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(job)
            await uow.workflows.remember_locator(
                job.id, LearnedStep(1, "component", "status", "evidence")
            )
            await uow.commit()

        await asyncio.gather(
            _learns(session_factory, job, "department"), _learns(session_factory, job, "region")
        )

        async with SqlUnitOfWork(session_factory) as uow:
            now = await uow.workflows.get(TENANT, job.id)
            learned = await uow.workflows.learned_for(job.id)
        assert [one.order for one in now.steps] == [0, 1, 2]
        assert [(one.ord, one.query) for one in learned] == [(2, "status")]

    async def test_a_mining_grow_waits_for_a_learned_field_and_keeps_it(
        self, session_factory: async_sessionmaker[AsyncSession], engine: AsyncEngine
    ) -> None:
        job, by_id = await _a_real_job(session_factory)
        proposal = replace(
            job,
            steps=[
                *job.steps,
                Step(order=2, says="press it", system=SYSTEM, cites=[_GESTURES[4].id]),
            ],
        )

        async def grows() -> None:
            async with SqlUnitOfWork(session_factory) as uow:
                await _grow(uow, tenant_id=TENANT, known_id=job.id, proposal=proposal, by_id=by_id)
                await uow.commit()

        await _against_an_open_grow(session_factory, engine, job, grows)

        steps, learned = await _now(session_factory, job)
        assert steps == ["type it", "Fill Department", "save it", "press it"]
        assert learned == [(1, "combobox|Department"), (2, "#save")]

    async def test_a_run_teaches_nothing_under_a_numbering_a_grow_is_replacing(
        self, session_factory: async_sessionmaker[AsyncSession], engine: AsyncEngine
    ) -> None:
        job, by_id = await _a_real_job(session_factory)
        sighted = {"strategy": "css", "query": "#seen", "frame_path": "[]"}

        async def teaches() -> None:
            await Teach(SqlUnitOfWork(session_factory), FakeClock()).learn(
                CTX,
                job,
                by_id,
                job.steps[1],
                (StepResult("done", Lane.SIGHT, learned=sighted),),
                run_id="run_old",
                values={},
            )

        await _against_an_open_grow(session_factory, engine, job, teaches)

        _, learned = await _now(session_factory, job)
        assert learned == [(1, "combobox|Department"), (2, "#save")]

    async def test_a_run_reads_no_locator_under_a_numbering_a_grow_is_replacing(
        self, session_factory: async_sessionmaker[AsyncSession], engine: AsyncEngine
    ) -> None:
        job, _ = await _a_real_job(session_factory)

        async def reads() -> Mapping[int, LearnedStep]:
            return await Teach(SqlUnitOfWork(session_factory), FakeClock()).locators(CTX, job)

        assert await _against_an_open_grow(session_factory, engine, job, reads) == {}

    async def test_learning_parameters_waits_for_a_learned_field_and_keeps_it(
        self, session_factory: async_sessionmaker[AsyncSession], engine: AsyncEngine
    ) -> None:
        twice = [{"name": "a", "key": "k"}, {"name": "b", "key": "k"}]
        job, _ = await _a_real_job(session_factory, parameters=twice)

        async def learns() -> None:
            async with SqlUnitOfWork(session_factory) as uow:
                await learn_parameters(
                    uow,
                    tenant_id=TENANT,
                    known_id=job.id,
                    proposal=replace(job, steps=[]),
                    by_id={},
                    intents={},
                )
                await uow.commit()

        await _against_an_open_grow(session_factory, engine, job, learns)

        steps, learned = await _now(session_factory, job)
        assert steps == ["type it", "Fill Department", "save it"]
        assert learned == [(1, "combobox|Department"), (2, "#save")]

    async def test_healing_the_steps_waits_for_a_learned_field_and_keeps_it(
        self, session_factory: async_sessionmaker[AsyncSession], engine: AsyncEngine
    ) -> None:
        job, _ = await _a_real_job(session_factory)

        async def heals() -> None:
            async with SqlUnitOfWork(session_factory) as uow:
                assert await fill_in_passwords(uow, tenant_id=TENANT) == 1
                await uow.commit()

        await _against_an_open_grow(session_factory, engine, job, heals)

        steps, learned = await _now(session_factory, job)
        assert steps == ["type it", "Fill Department", "save it"]
        assert learned == [(1, "combobox|Department"), (2, "#save")]

    async def test_a_grow_stopped_mid_way_leaves_the_job_to_the_learning_that_waited(
        self, session_factory: async_sessionmaker[AsyncSession], engine: AsyncEngine
    ) -> None:
        job, _ = await _a_real_job(session_factory)

        await _against_an_open_grow(
            session_factory,
            engine,
            job,
            lambda: _learns(session_factory, job, "region"),
            stopped=True,
        )

        steps, learned = await _now(session_factory, job)
        assert steps == ["type it", "Fill Region", "save it"]
        assert learned == [(2, "#save")]

    async def test_a_mining_pass_holds_no_job_s_row_while_it_asks_the_model(
        self, session_factory: async_sessionmaker[AsyncSession], engine: AsyncEngine
    ) -> None:
        """The pass's listing says the job needs healing; by the locked re-read a
        heal has landed and there is nothing left to do. That re-read's lock must
        still end before the model is asked -- a call of up to minutes -- or every
        run's learning on the job waits for it."""
        job, by_id = await _a_real_job(session_factory)
        asker = _AsksAndWaits()

        async def mines() -> None:
            async with SqlUnitOfWork(session_factory) as uow:
                await mine(
                    uow,
                    tenant_id=TENANT,
                    asker=asker,
                    locks=FakeAccountLocks(),
                    now=datetime(2025, 2, 11, 23, tzinfo=UTC),
                    cap_usd=100.0,
                )

        async with SqlUnitOfWork(session_factory) as healer:
            held = await healer.workflows.get(TENANT, job.id, lock=True)
            assert _healed(held, by_id)
            await healer.workflows.save(held)
            mining = asyncio.ensure_future(mines())
            await _until_it_waits_or_ends(engine, mining)
            await healer.commit()
        asking = asyncio.ensure_future(asker.asked_at.wait())
        await asyncio.wait({mining, asking}, return_when=asyncio.FIRST_COMPLETED)
        assert asker.asked_at.is_set()

        async with SqlUnitOfWork(session_factory) as uow:
            healed = await uow.workflows.get(TENANT, job.id)
        learning = asyncio.ensure_future(_learns(session_factory, healed, "department"))
        await _until_it_waits_or_ends(engine, learning)
        learned_while_asking = learning.done()
        asker.answer.set()
        await asyncio.gather(mining, learning)

        assert learned_while_asking
        steps, _ = await _now(session_factory, job)
        assert "Fill Department" in steps

    async def test_a_run_s_pin_is_written_once(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        job = _workflow()
        run = _run(job.id, outcome="running", pinned=pin(job))
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflows.save(job)
            await uow.workflow_runs.save(run)
            await uow.commit()
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.workflow_runs.save(replace(run, pinned=pin(replace(job, steps=[]))))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            back = await uow.workflow_runs.get(TENANT, run.id)
        assert back is not None and back.pinned == job


CTX = RequestContext(tenant_id=TENANT, principal_id=PrincipalId("clerk"))
_GESTURES = _gestures(TENANT.value)
SYSTEM = _GESTURES[0].system


async def _a_real_job(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    parameters: list[dict[str, object]] | None = None,
) -> tuple[Workflow, dict[str, Gesture]]:
    """Type, then save, citing real gestures, stored with them and with a
    locator learned for the save."""
    job = _workflow(
        systems=[SYSTEM],
        steps=[
            Step(order=0, says="type it", system=SYSTEM, cites=[_GESTURES[0].id]),
            Step(order=1, says="save it", system=SYSTEM, cites=[_GESTURES[3].id]),
        ],
        parameters=parameters or [],
        signs_in=None,
    )
    async with SqlUnitOfWork(session_factory) as uow:
        await uow.gestures.add_gestures(tuple(_GESTURES))
        await uow.workflows.save(job)
        await uow.workflows.remember_locator(job.id, LearnedStep(1, "css", "#save", "sight"))
        await uow.commit()
    return job, {one.id: one for one in _GESTURES}


async def _learns(
    session_factory: async_sessionmaker[AsyncSession], job: Workflow, name: str
) -> None:
    await Teach(SqlUnitOfWork(session_factory), FakeClock()).learn_field(
        CTX,
        job,
        Composed(name, name.title(), "combobox", 1),
        key=name,
        value="x",
        learned={},
        lane=Lane.UI,
        run_id=f"run_{name}",
    )


async def _against_an_open_grow[T](
    session_factory: async_sessionmaker[AsyncSession],
    engine: AsyncEngine,
    job: Workflow,
    other: Callable[[], Awaitable[T]],
    *,
    stopped: bool = False,
) -> T:
    """Grows `job` by a Department field before its save, as `learn_field`
    does, and holds that open while `other` runs; commits once `other` is
    waiting on a lock (or has finished without one), or rolls back when
    `stopped`."""
    async with SqlUnitOfWork(session_factory) as grow:
        held = await grow.workflows.get(TENANT, job.id, lock=True)
        grown, moved = with_field(
            held, Composed("department", "Department", "combobox", 1), key="department", value="x"
        )
        await grow.workflows.grew(grown, moved=moved)
        await grow.workflows.remember_locator(
            job.id, LearnedStep(1, "role_and_name", "combobox|Department", "composed")
        )
        running = asyncio.ensure_future(other())
        await _until_it_waits_or_ends(engine, running)
        if not stopped:
            await grow.commit()
    return await running


async def _until_it_waits_or_ends(engine: AsyncEngine, running: asyncio.Future[Any]) -> None:
    """Returns once some session waits on a lock, or `running` has finished."""
    async with engine.connect() as watching:
        while not running.done():
            waiting = await watching.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity"
                    " WHERE datname = current_database() AND wait_event_type = 'Lock'"
                )
            )
            if waiting:
                return
            await asyncio.sleep(0.01)


class _AsksAndWaits(FakeAsker):
    """A model call that holds until `answer` is set, and says when it began."""

    def __init__(self) -> None:
        super().__init__()
        self.asked_at = asyncio.Event()
        self.answer = asyncio.Event()

    async def ask(self, **question: Any) -> Answer:
        self.asked_at.set()
        await self.answer.wait()
        return await super().ask(**question)


async def _now(
    session_factory: async_sessionmaker[AsyncSession], job: Workflow
) -> tuple[list[str], list[tuple[int, str]]]:
    async with SqlUnitOfWork(session_factory) as uow:
        now = await uow.workflows.get(TENANT, job.id)
        learned = await uow.workflows.learned_for(job.id)
    return [one.says for one in now.steps], sorted((one.ord, one.query) for one in learned)
