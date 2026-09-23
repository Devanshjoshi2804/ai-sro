from __future__ import annotations

import asyncio
import logging
import os
import socket
from datetime import UTC, datetime, timedelta

from temporalio.client import Client
from temporalio.worker import Worker

from sro.application.context import RequestContext
from sro.application.observation.mining_pass import rekey_workflows
from sro.config import Settings, get_settings
from sro.container import Container, build_container
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.infrastructure.temporal.activities import Activities
from sro.infrastructure.temporal.queues import BROWSER_QUEUE, DEFAULT_QUEUE
from sro.infrastructure.temporal.workflows import (
    ExecutionWorkflow,
    InductionWorkflow,
    RecordingSessionWorkflow,
    TriggerWorkflow,
)
from sro.observability import configure_logging

logger = logging.getLogger("sro.infrastructure.temporal.worker")


def identity(settings: Settings) -> str:
    return f"{os.getpid()}@{socket.gethostname()}@{settings.revision}"


async def connect(settings: Settings) -> Client:
    return await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)


async def keep_sessions_open(container: Container, every_seconds: float) -> None:
    while True:
        await asyncio.sleep(every_seconds)
        try:
            swept = await container.keep_sessions_open().sweep()
        except Exception:
            logger.exception("the session keeper could not finish its sweep")
            continue
        if swept.open_now or swept.unreachable or swept.released:
            logger.info(
                "sessions kept open: %s; unreachable: %s; left alone: %s; browsers released: %s",
                ", ".join(swept.open_now) or "none",
                ", ".join(swept.unreachable) or "none",
                ", ".join(swept.left_alone) or "none",
                ", ".join(swept.released) or "none",
            )


async def mine_lately(container: Container, every_seconds: float, window_hours: int) -> None:
    if every_seconds <= 0:
        logger.info("the observation miner is off (mining_sweep_seconds=0)")
        return
    while True:
        await asyncio.sleep(every_seconds)
        since = datetime.now(UTC) - timedelta(hours=window_hours)
        try:
            mined = await container.mine_everything().execute(since=since)
        except Exception:
            logger.exception("the miner could not finish its sweep")
            continue
        for tenant, found in mined.items():
            if found.candidates_new or found.occurrences_new:
                logger.info(
                    "%s: %s new tasks noticed, %s more doings of ones already known",
                    tenant,
                    found.candidates_new,
                    found.occurrences_new,
                )

        for tenant in mined:
            ctx = RequestContext(tenant_id=TenantId(tenant), principal_id=PrincipalId("miner"))
            try:
                learned = await container.learn_what_repeats().execute(ctx)
            except Exception:
                logger.exception("%s: the learner could not finish its pass", tenant)
                continue
            for skill_id in learned.skills:
                logger.info("%s: learned a task nobody demonstrated -- %s", tenant, skill_id)
            for waiting in learned.still_waiting:
                logger.info("%s: waiting for a demonstration -- %s", tenant, waiting)


async def mine_the_rig_lately(container: Container, every_seconds: float) -> None:
    if every_seconds <= 0:
        logger.info("the rig miner is off (rig_sweep_seconds=0)")
        return
    while True:
        await asyncio.sleep(every_seconds)
        try:
            mined = await container.mine_lately().execute(now=datetime.now(UTC))
        except Exception:
            logger.exception("the rig miner could not finish its sweep")
            continue
        for tenant, result in mined.items():
            if result.error:
                continue
            if result.read or result.kept or result.learned_parameters:
                logger.info(
                    "%s: %s gesture(s) read, %s job(s) kept of %s proposed,"
                    " %s parameter(s) learned",
                    tenant,
                    result.read,
                    result.kept,
                    result.proposed,
                    result.learned_parameters,
                )


async def retain_lately(container: Container, every_seconds: float) -> None:
    while True:
        await asyncio.sleep(every_seconds)
        try:
            forgotten = await container.sweep_retention().execute()
        except Exception:
            logger.exception("the retention sweep could not finish")
            continue
        for tenant, gone in forgotten.items():
            if gone.batches:
                logger.info(
                    "%s: %s batch(es) past their retention window removed", tenant, gone.batches
                )


async def rekey_everything(container: Container) -> int:
    async with container.unit_of_work() as uow:
        tenants = await uow.gestures.tenants_since(datetime(1970, 1, 1, tzinfo=UTC))
    changed = 0
    for tenant in tenants:
        async with container.unit_of_work() as uow:
            changed += await rekey_workflows(uow, tenant_id=tenant)
    return changed


async def run() -> None:
    settings = get_settings()
    _settings = get_settings()
    configure_logging(
        as_json=_settings.environment != "local",
        louder_for=frozenset(one.strip() for one in _settings.louder_for.split(",") if one.strip()),
    )
    logger.info("worker starting on revision %s", settings.revision)
    container = build_container(settings)
    activities = Activities(container)
    client = await connect(settings)
    me = identity(settings)

    default = Worker(
        client,
        identity=me,
        task_queue=DEFAULT_QUEUE,
        workflows=[InductionWorkflow, ExecutionWorkflow, TriggerWorkflow],
        activities=[
            activities.induce_skill,
            activities.start_run,
            activities.execute_step,
            activities.finish_run,
            activities.fire_trigger,
        ],
    )
    browser = Worker(
        client,
        identity=me,
        task_queue=BROWSER_QUEUE,
        workflows=[RecordingSessionWorkflow],
        activities=[activities.abandon_stale_recording, activities.close_browser_session],
    )

    try:
        rekeyed = await rekey_everything(container)
        if rekeyed:
            logger.info("%s workflow(s) had their shape key recomputed", rekeyed)
    except Exception:
        logger.exception("the shape keys could not be recomputed")

    keeper = asyncio.create_task(keep_sessions_open(container, settings.session_sweep_seconds))
    miner = asyncio.create_task(
        mine_lately(container, settings.mining_sweep_seconds, settings.mining_window_hours)
    )
    rig_miner = asyncio.create_task(mine_the_rig_lately(container, settings.rig_sweep_seconds))
    retainer = asyncio.create_task(retain_lately(container, settings.retention_sweep_seconds))
    try:
        async with default, browser:
            await asyncio.Future()
    finally:
        keeper.cancel()
        miner.cancel()
        rig_miner.cancel()
        retainer.cancel()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
