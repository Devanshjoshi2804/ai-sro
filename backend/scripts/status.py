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

POLLED_WITHIN = timedelta(seconds=120)


def tree() -> str:
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
    except Exception as why:
        return f"-- not answering ({type(why).__name__})"


async def worker_revisions(settings: Settings, here: str) -> str:
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
    order = sorted(alive.items(), key=lambda seen: (seen[0] != here, seen[0]))
    return "; ".join(f"{count} polling on {marked(revision, here)}" for revision, count in order)


def reported(identity: str) -> str:
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
