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
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from temporalio.api.enums.v1 import TaskQueueType
from temporalio.api.taskqueue.v1 import TaskQueue
from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest
from temporalio.client import Client

from sro.config import Settings, get_settings
from sro.infrastructure.temporal.queues import DEFAULT_QUEUE

ROOT = Path(__file__).resolve().parents[2]

UNMARKED = "unmarked"
"""What a process started before this change reports: nothing.

Shown rather than hidden. A process that is genuinely running and cannot say
which code it is running is the oldest thing on the machine, and that line is
the one this tool exists to print."""

POLLED_WITHIN = timedelta(seconds=120)
"""How recently a poller must have been seen for its revision to be reported.

Temporal keeps poller history for around five minutes, so ``described.pollers``
is largely a record of the recently dead. Reporting all of it had this tool
naming two phantom stale workers on a machine running exactly one -- and a
status line that cries wolf gets ignored, which is the failure this whole thing
exists to prevent.

A worker long-polls on a 60s timeout and the server stamps ``last_access_time``
as each poll arrives, so a live worker refreshes at least once a minute. Two of
those cycles: one missed refresh is forgiven, and a killed worker is off the
line inside two minutes instead of five. Much tighter and a worker between polls
would vanish, which is its own kind of lie.
"""


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
            return str(answered.json().get("revision") or UNMARKED)
    # Any failure at all means the same thing here: nobody answered.
    except Exception as why:
        return f"-- not answering ({type(why).__name__})"


async def worker_revisions(settings: Settings, here: str) -> str:
    """Asked of Temporal, which already knows every process polling its queues.

    The worker puts its revision in the identity it polls with, so this needs no
    table and no log file, and -- unlike a row written at startup -- it is empty
    when the worker has died rather than stale. Counted rather than listed: two
    workers on one revision is a normal Tuesday, two on different revisions is a
    deploy in flight, and the difference is worth seeing.
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
    seen_since = datetime.now(UTC) - POLLED_WITHIN
    alive = Counter(
        reported(poller.identity)
        for poller in described.pollers
        if poller.last_access_time.ToDatetime(tzinfo=UTC) > seen_since
    )
    if not alive:
        return "-- nothing polling"
    # The working tree's own revision first, so anything that is not it reads as
    # the exception rather than being hunted for in an alphabetical list.
    order = sorted(alive.items(), key=lambda seen: (seen[0] != here, seen[0]))
    return "; ".join(f"{count} polling on {marked(revision, here)}" for revision, count in order)


def reported(identity: str) -> str:
    """The revision out of a ``pid@host@revision`` Temporal identity.

    Two fields is Temporal's own default, which is what a worker from before
    this change polls with."""
    fields = identity.split("@")
    return fields[-1] if len(fields) > 2 else UNMARKED


def marked(revision: str, here: str) -> str:
    return revision if revision == here else f"{revision} <-- not the working tree"


async def main() -> None:
    settings = get_settings()
    here = tree()
    api = await api_revision(settings.api_url)
    running = {
        f"api ({settings.api_url})": api if api.startswith("--") else marked(api, here),
        f"worker ({settings.temporal_address})": await worker_revisions(settings, here),
    }

    print(f"{'working tree':<34} {here}")
    for what, reports in running.items():
        print(f"{what:<34} {reports}")


if __name__ == "__main__":
    asyncio.run(main())
