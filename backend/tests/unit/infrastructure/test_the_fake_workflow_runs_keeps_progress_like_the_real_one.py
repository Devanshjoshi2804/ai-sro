"""The workflow-run fake's `progress` rule, held to the same rule
`tests/integration/test_workflow_run_repositories.py::TestProgressWrittenOnlyByRecordProgress`
proves of the SQL: `save` writes `progress` only on a row's first insert, and
`record_progress` is the only path that ever changes it again. A fake that let
a later `save` roll `progress` back would pass every use case built on it
against a lie the real store does not tell.
"""

from __future__ import annotations

from typing import Any

from sro.domain.execution.workflow_run import WorkflowRun, new_run_id
from sro.domain.shared.identifiers import TenantId
from tests.unit.fakes import FakeWorkflowRunRepository

TENANT = TenantId("acme")


def _run(**overrides: Any) -> WorkflowRun:
    fields: dict[str, Any] = {
        "id": new_run_id(),
        "tenant": TENANT.value,
        "workflow_id": "wfl_1",
        "device_id": "",
        "executor": "steel",
        "values": {},
        "started_by": "form",
        "live": False,
        "allow_focus": True,
        "started_at": "2026-09-05T10:00:00+00:00",
    }
    fields.update(overrides)
    return WorkflowRun(**fields)


async def test_the_first_save_writes_the_initial_progress() -> None:
    runs = FakeWorkflowRunRepository()
    run = _run(progress={"step": 0, "lease": "lse_1"})

    await runs.save(run)

    back = await runs.get(TENANT, run.id)
    assert back is not None and back.progress == {"step": 0, "lease": "lse_1"}


async def test_a_stale_save_does_not_roll_progress_back() -> None:
    runs = FakeWorkflowRunRepository()
    run = _run()
    await runs.save(run)

    stale_copy = await runs.get(TENANT, run.id)
    assert stale_copy is not None

    await runs.record_progress(run.id, {"step": 1, "marks": {"0": {"wrote": "done"}}})
    stale_copy.watched = True
    await runs.save(stale_copy)

    back = await runs.get(TENANT, run.id)
    assert back is not None
    assert back.watched is True
    assert back.progress == {"step": 1, "marks": {"0": {"wrote": "done"}}}
