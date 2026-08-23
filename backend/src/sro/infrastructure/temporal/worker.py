"""Worker process. ``make worker`` runs this.

Two task queues: ``browser`` for anything holding a scarce browser slot,
``default`` for everything else. Splitting them now means a slow induction can
never starve session reaping.
"""

from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from sro.config import Settings, get_settings
from sro.container import Container, build_container
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
    try:
        async with default, browser:
            await asyncio.Future()
    finally:
        keeper.cancel()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
