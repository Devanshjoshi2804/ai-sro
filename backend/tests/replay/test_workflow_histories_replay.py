"""Every committed `RunWorkflow` history replays on the current code. A change
to the workflow's commands that is not behind `workflow.patched()` fails here,
not on a run paused across a deploy. Record them with `make record-histories`."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from temporalio.client import WorkflowHistory
from temporalio.worker import Replayer

from sro.infrastructure.temporal.workflows import RunWorkflow

HISTORIES = Path(__file__).parent / "histories"


async def _histories() -> AsyncIterator[WorkflowHistory]:
    for path in sorted(HISTORIES.glob("*.json")):
        yield WorkflowHistory.from_json(path.stem, path.read_text())


async def test_every_recorded_history_replays_on_the_current_workflow() -> None:
    assert list(HISTORIES.glob("*.json"))

    results = await Replayer(workflows=[RunWorkflow]).replay_workflows(
        _histories(), raise_on_replay_failure=False
    )

    assert {run: str(why) for run, why in results.replay_failures.items()} == {}
