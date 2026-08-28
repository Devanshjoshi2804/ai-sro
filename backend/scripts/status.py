"""What each running process says it is running, beside what the tree says.

``make status``. Written after an API that had been up for two days kept serving
a rule that had been fixed an hour earlier: the message named a real rule and
quoted real parameter names, so every step of the diagnosis pointed at the code,
and the answer was in the process table.

Reports, never enforces. Two revisions at once is what a rolling deploy looks
like, and a check that refused to run on a mismatch would stop one dead.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import httpx
from temporalio.api.enums.v1 import TaskQueueType
from temporalio.api.taskqueue.v1 import TaskQueue
from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest
from temporalio.client import Client

from sro.config import Settings, get_settings
from sro.infrastructure.temporal.queues import DEFAULT_QUEUE

ROOT = Path(__file__).resolve().parents[2]

# A process started before any of this existed reports nothing, and saying so is
# the whole point -- it is by definition the oldest thing running.
SILENT = "-- says nothing (started before it could)"


def tree() -> str:
    """What the checkout is on right now -- the thing everything else is compared to."""
    done = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607 - git is on PATH or it is not
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.stdout.strip() or "unknown"


async def api_revision(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=3.0) as http:
            answered = await http.get(f"{url}/health")
            answered.raise_for_status()
            return str(answered.json().get("revision") or SILENT)
    # Any failure at all means the same thing here: nobody answered.
    except Exception as why:
        return f"-- not answering ({type(why).__name__})"


async def worker_revision(settings: Settings) -> str:
    """Asked of Temporal, which already knows every process polling its queues.

    The worker puts its revision in the identity it polls with, so this needs no
    table and no log file, and -- unlike a row written at startup -- it is empty
    when the worker has died rather than stale.
    """
    try:
        client = await Client.connect(
            settings.temporal_address, namespace=settings.temporal_namespace
        )
        described = await client.workflow_service.describe_task_queue(
            DescribeTaskQueueRequest(
                namespace=settings.temporal_namespace,
                task_queue=TaskQueue(name=DEFAULT_QUEUE),
                task_queue_type=TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW,
            )
        )
    # Same again -- no answer is the answer.
    except Exception as why:
        return f"-- temporal not answering ({type(why).__name__})"
    polling = sorted({reported(poller.identity) for poller in described.pollers})
    return ", ".join(polling) or "-- not polling"


def reported(identity: str) -> str:
    """The revision out of a ``pid@host@revision`` Temporal identity.

    Two fields is Temporal's own default, which is what a worker from before
    this change polls with."""
    fields = identity.split("@")
    return fields[-1] if len(fields) > 2 else SILENT


async def main() -> None:
    settings = get_settings()
    here = tree()
    running = {
        f"api ({settings.api_url})": await api_revision(settings.api_url),
        f"worker ({settings.temporal_address})": await worker_revision(settings),
    }

    print(f"{'working tree':<34} {here}")
    for what, revision in running.items():
        stale = " <-- not the working tree" if revision.isalnum() and revision != here else ""
        print(f"{what:<34} {revision}{stale}")


if __name__ == "__main__":
    asyncio.run(main())
