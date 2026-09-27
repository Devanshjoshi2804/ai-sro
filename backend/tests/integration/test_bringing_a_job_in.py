"""The sweep brings every stored job under the typed-values rule once (M3).

Real Postgres, because what is proved is locking: the sweep saves under the
job's row lock as a compare-and-set on `parameters_rule`, so a field a run
learned at the same moment survives, two sweeps bring a job in once, and a
sweep that crashes or is stopped mid-way leaves the job to the next one.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from sro.application.observation.mining_pass import bring_in_parameters
from sro.domain.skill.learned import K_PARAMETERS_RULE
from sro.domain.skill.workflow import Workflow
from sro.infrastructure.db import workflows as workflows_module
from sro.infrastructure.db.repositories import SqlUnitOfWork
from tests.integration.test_workflow_repositories import (
    TENANT,
    _a_real_job,
    _against_an_open_grow,
    _learns,
    _now,
    _until_it_waits_or_ends,
)


async def _brings_in(session_factory: async_sessionmaker[AsyncSession], job: Workflow) -> int:
    async with SqlUnitOfWork(session_factory) as uow:
        return await bring_in_parameters(uow, TENANT, [job])


async def _state(
    session_factory: async_sessionmaker[AsyncSession], job: Workflow
) -> tuple[int | None, list[str]]:
    async with SqlUnitOfWork(session_factory) as uow:
        now = await uow.workflows.get(TENANT, job.id)
    async with session_factory() as session:
        rule = await session.scalar(
            text("SELECT parameters_rule FROM workflows WHERE id = :id"), {"id": job.id}
        )
    return rule, sorted(str(one["name"]) for one in now.parameters)


async def test_the_store_lists_jobs_behind_the_rule_and_stamps_each_once(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    job, _ = await _a_real_job(session_factory)
    async with SqlUnitOfWork(session_factory) as uow:
        assert await uow.workflows.behind_the_rule(K_PARAMETERS_RULE) == ()
        await uow.workflows.decide_signs_in(TENANT, job.id, False)
        await uow.workflows.place(TENANT, job.id, ("ges_b", "ges_a"))
        await uow.commit()

    async with SqlUnitOfWork(session_factory) as uow:
        assert [one.id for one in await uow.workflows.behind_the_rule(K_PARAMETERS_RULE)] == [
            job.id
        ]
        assert await uow.workflows.placed_on(TENANT, job.id) == ("ges_a", "ges_b")
        assert await uow.workflows.ruled(TENANT, job.id, K_PARAMETERS_RULE)
        assert not await uow.workflows.ruled(TENANT, job.id, K_PARAMETERS_RULE)
        await uow.commit()
    async with SqlUnitOfWork(session_factory) as uow:
        assert await uow.workflows.behind_the_rule(K_PARAMETERS_RULE) == ()
        assert await uow.workflows.behind_the_rule(K_PARAMETERS_RULE + 1) != ()


async def test_the_sweep_waits_for_a_learned_field_and_keeps_it(
    session_factory: async_sessionmaker[AsyncSession], engine: AsyncEngine
) -> None:
    job, _ = await _a_real_job(session_factory)

    brought = await _against_an_open_grow(
        session_factory, engine, job, lambda: _brings_in(session_factory, job)
    )

    steps, learned = await _now(session_factory, job)
    assert steps == ["type it", "Fill Department", "save it"]
    assert learned == [(1, "combobox|Department"), (2, "#save")]
    assert brought == 1
    assert await _state(session_factory, job) == (K_PARAMETERS_RULE, ["Client Code", "department"])


async def test_a_field_learned_while_the_sweep_holds_the_job_lands_after_it(
    session_factory: async_sessionmaker[AsyncSession], engine: AsyncEngine
) -> None:
    job, _ = await _a_real_job(session_factory)

    async with SqlUnitOfWork(session_factory) as sweep:
        await sweep.workflows.get(TENANT, job.id, lock=True)
        learning = asyncio.ensure_future(_learns(session_factory, job, "department"))
        await _until_it_waits_or_ends(engine, learning)
        assert not learning.done(), "the run did not wait for the sweep"
        assert await bring_in_parameters(sweep, TENANT, [job]) == 1
    await learning

    steps, _ = await _now(session_factory, job)
    assert steps == ["type it", "Fill Department", "save it"]
    assert await _state(session_factory, job) == (K_PARAMETERS_RULE, ["Client Code", "department"])


async def test_two_sweeps_at_once_bring_a_job_in_once(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    job, _ = await _a_real_job(session_factory)

    brought = await asyncio.gather(
        _brings_in(session_factory, job), _brings_in(session_factory, job)
    )

    assert sorted(brought) == [0, 1]
    assert await _state(session_factory, job) == (K_PARAMETERS_RULE, ["Client Code"])


async def test_a_sweep_that_crashes_between_the_stamp_and_the_save_leaves_the_job_behind(
    session_factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    job, _ = await _a_real_job(session_factory)
    saving = workflows_module.SqlWorkflowRepository.save

    async def _dies(self: workflows_module.SqlWorkflowRepository, workflow: Workflow) -> None:
        raise RuntimeError("the worker died")

    monkeypatch.setattr(workflows_module.SqlWorkflowRepository, "save", _dies)
    assert await _brings_in(session_factory, job) == 0
    assert await _state(session_factory, job) == (None, [])

    monkeypatch.setattr(workflows_module.SqlWorkflowRepository, "save", saving)
    assert await _brings_in(session_factory, job) == 1
    assert await _state(session_factory, job) == (K_PARAMETERS_RULE, ["Client Code"])


async def test_a_sweep_stopped_while_it_waits_writes_nothing(
    session_factory: async_sessionmaker[AsyncSession], engine: AsyncEngine
) -> None:
    job, _ = await _a_real_job(session_factory)

    async with SqlUnitOfWork(session_factory) as other:
        await other.workflows.get(TENANT, job.id, lock=True)
        running = asyncio.ensure_future(_brings_in(session_factory, job))
        await _until_it_waits_or_ends(engine, running)
        running.cancel()
        with suppress(asyncio.CancelledError):
            await running
        await other.commit()

    assert await _state(session_factory, job) == (None, [])
    assert await _brings_in(session_factory, job) == 1
