from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import socket
from datetime import UTC, datetime, timedelta

from temporalio.client import Client
from temporalio.worker import Worker

from sro.application.observation.mining_pass import rekey_workflows
from sro.config import Settings, get_settings
from sro.container import Container, build_container
from sro.domain.execution.progress import K_STEP_HEARTBEAT_S
from sro.infrastructure.temporal.activities import Activities, RunActivities
from sro.infrastructure.temporal.queues import DEFAULT_QUEUE, RUNS_QUEUE
from sro.infrastructure.temporal.workflows import ExecutionWorkflow, RunWorkflow, TriggerWorkflow
from sro.observability import configure_logging

logger = logging.getLogger("sro.infrastructure.temporal.worker")

_STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT)


def identity(settings: Settings) -> str:
    return f"{os.getpid()}@{socket.gethostname()}@{settings.revision}"


async def connect(settings: Settings) -> Client:
    return await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)


async def until_signalled(*workers: Worker) -> None:
    loop = asyncio.get_running_loop()
    stopping = asyncio.Event()
    for one in _STOP_SIGNALS:
        loop.add_signal_handler(one, stopping.set)
    try:
        async with contextlib.AsyncExitStack() as serving:
            for worker in workers:
                await serving.enter_async_context(worker)
            await stopping.wait()
            logger.info("stopping: letting running activities finish first")
    finally:
        for one in _STOP_SIGNALS:
            loop.remove_signal_handler(one)


async def keep_sessions_open(container: Container, every_seconds: float) -> None:
    while True:
        await asyncio.sleep(every_seconds)
        try:
            expired = await container.expire_confirmations().execute()
        except Exception:
            logger.exception("the confirmation sweep could not finish")
        else:
            for tenant, count in expired.items():
                logger.info("%s: %s confirmation(s) expired unanswered", tenant, count)
        try:
            swept = await container.keep_sessions_open().sweep()
        except Exception:
            logger.exception("the session keeper could not finish its sweep")
            continue
        if swept.open_now or swept.unreachable or swept.released:
            logger.info(
                "sessions kept open: %s; unreachable: %s; left alone: %s; contexts released: %s",
                ", ".join(swept.open_now) or "none",
                ", ".join(swept.unreachable) or "none",
                ", ".join(swept.left_alone) or "none",
                ", ".join(swept.released) or "none",
            )


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


async def look_in_the_mail_lately(container: Container, every_seconds: float) -> None:
    if every_seconds <= 0:
        logger.info("the mail poll is off (mail_sweep_seconds=0)")
        return
    while True:
        await asyncio.sleep(every_seconds)
        try:
            looked = await container.look_in_the_mail_lately().execute()
        except Exception:
            logger.exception("the mail poll could not finish")
            continue
        for who, one in looked.items():
            if one.read:
                logger.info("%s: %s mail(s) read -- %s", who, one.read, one.why)


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
        workflows=[ExecutionWorkflow, TriggerWorkflow],
        activities=[
            activities.start_run,
            activities.execute_step,
            activities.finish_run,
            activities.fire_trigger,
        ],
    )
    run_activities = RunActivities(container)
    runs = Worker(
        client,
        identity=me,
        task_queue=RUNS_QUEUE,
        graceful_shutdown_timeout=timedelta(seconds=K_STEP_HEARTBEAT_S),
        workflows=[RunWorkflow],
        activities=[
            run_activities.prepare,
            run_activities.acquire,
            run_activities.step,
            run_activities.stopped,
            run_activities.finish,
            run_activities.release,
        ],
    )
    try:
        rekeyed = await rekey_everything(container)
        if rekeyed:
            logger.info("%s workflow(s) had their shape key recomputed", rekeyed)
    except Exception:
        logger.exception("the shape keys could not be recomputed")

    keeper = asyncio.create_task(keep_sessions_open(container, settings.session_sweep_seconds))
    rig_miner = asyncio.create_task(mine_the_rig_lately(container, settings.rig_sweep_seconds))
    retainer = asyncio.create_task(retain_lately(container, settings.retention_sweep_seconds))
    mailer = asyncio.create_task(look_in_the_mail_lately(container, settings.mail_sweep_seconds))
    try:
        await until_signalled(default, runs)
    finally:
        keeper.cancel()
        rig_miner.cancel()
        retainer.cancel()
        mailer.cancel()
        await container.driver.aclose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
