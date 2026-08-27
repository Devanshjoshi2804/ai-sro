"""Worker process. ``make worker`` runs this.

Two task queues: ``browser`` for anything holding a scarce browser slot,
``default`` for everything else. Splitting them now means a slow induction can
never starve session reaping.
"""

from __future__ import annotations

import asyncio
import logging
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
    container = build_container(settings)
    activities = Activities(container)
    client = await connect(settings)

    default = Worker(
        client,
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
        task_queue=BROWSER_QUEUE,
        workflows=[RecordingSessionWorkflow],
        activities=[activities.abandon_stale_recording, activities.close_browser_session],
    )

    keeper = asyncio.create_task(keep_sessions_open(container, settings.session_sweep_seconds))
    miner = asyncio.create_task(
        mine_lately(container, settings.mining_sweep_seconds, settings.mining_window_hours)
    )
    retainer = asyncio.create_task(retain_lately(container, settings.retention_sweep_seconds))
    try:
        async with default, browser:
            await asyncio.Future()
    finally:
        keeper.cancel()
        miner.cancel()
        retainer.cancel()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
