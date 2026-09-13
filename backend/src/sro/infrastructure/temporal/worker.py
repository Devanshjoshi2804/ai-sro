"""Worker process. ``make worker`` runs this.

Two task queues: ``browser`` for anything holding a scarce browser slot,
``default`` for everything else. Splitting them now means a slow induction can
never starve session reaping.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
from datetime import UTC, datetime, timedelta

from temporalio.client import Client
from temporalio.worker import Worker

from sro.application.context import RequestContext
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

logger = logging.getLogger(__name__)


def identity(settings: Settings) -> str:
    """How this worker names itself to Temporal: ``pid@host@revision``.

    Temporal's default is ``pid@host``; the revision is appended because that is
    the field the server already keeps for every process polling a queue and
    hands back from DescribeTaskQueue. So the worker reports which code it is
    running without a new table, a new endpoint, or a log file to tail -- and it
    reports it live, which a row written at startup by a process since killed
    would not. `make status` reads the last ``@``-separated field.
    """
    return f"{os.getpid()}@{socket.gethostname()}@{settings.revision}"


async def connect(settings: Settings) -> Client:
    return await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)


async def keep_sessions_open(container: Container, every_seconds: float) -> None:
    """Sign systems back in before they expire, for as long as this runs.

    A loop in the worker rather than a scheduled workflow: it holds no state
    worth replaying, a missed sweep is corrected by the next one, and the
    cheapest thing that keeps a connection alive over a weekend is the right
    amount of machinery for it.
    """
    while True:
        await asyncio.sleep(every_seconds)
        try:
            swept = await container.keep_sessions_open().sweep()
        except Exception:
            # A keeper that dies quietly is worse than no keeper: the sessions
            # look fine until the morning somebody needs one.
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
    """Notice what somebody keeps doing, for as long as this runs.

    A loop for the same reasons as the keeper above: nothing to replay, and a
    missed sweep costs nothing because the next one reads the same window. Every
    episode already recorded is skipped, so running it often is only the price
    of reading the evidence again.
    """
    if every_seconds <= 0:
        # The pre-rig miner, left to a deliberate call. `Settings`' own field
        # carries the whole argument; the short of it is that this sweep
        # teaches what it notices without asking anybody, and four of the nine
        # skills it has taught are Gmail's sync endpoint or this console's own
        # Learn button. Returning rather than looping so the task finishes and
        # the worker is not holding a coroutine that will never do anything.
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

        # And anything now done often enough is learned, without waiting for
        # somebody to press a button. What comes out sits at the bottom of the
        # promotion ladder; nothing here lets anything run.
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
    """Read each recorded tenant's day, for as long as this runs.

    The rig's whole learning cycle, where `mine_lately` above is the pre-rig
    miner. Both halves had a person in them: `mine_pass` was reachable from a
    door and a script, `read_gestures` from a door and the crontab line in
    `sro.cli.read_cron`'s own docstring. Every mining result this project has
    measured came from somebody running a script.

    A loop for the same reasons as the keeper: nothing worth replaying, and a
    missed sweep is corrected by the next one reading the same window. What one
    pass costs is bounded by `daily_usd_cap`, checked before the window is
    packed, and a tenant over it is logged by `MineLately` and skipped rather
    than raised.

    Sleeps first. A worker restarting in a crash loop would otherwise fire the
    most expensive call in the system on every start.
    """
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
    """Delete evidence that has aged out of its tenant's own window.

    A loop for the same reason as the keeper and the miner: nothing here needs
    replaying, and a missed sweep costs one more day of storage rather than a
    broken promise -- the next sweep finds the same rows and removes them.
    """
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


async def run() -> None:
    settings = get_settings()
    configure_logging()
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
