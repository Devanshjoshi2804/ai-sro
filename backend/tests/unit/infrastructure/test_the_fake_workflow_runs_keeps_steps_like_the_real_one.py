"""The workflow-run fake's step-history rule, held to the same rule
`tests/integration/test_workflow_run_repositories.py::TestWorkflowRuns::test_a_stale_save_does_not_erase_a_step_the_worker_added`
proves of the SQL: `save` upserts the steps it carries by `order` and never
deletes a step it doesn't carry. A fake that still replaced the whole step
list on every save would pass every use case built on it against a lie the
real store no longer tells.
"""

from __future__ import annotations

from typing import Any

from sro.domain.execution.workflow_run import RunStep, WorkflowRun, new_run_id
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


async def test_a_stale_save_does_not_erase_a_step_the_worker_added() -> None:
    runs = FakeWorkflowRunRepository()
    run = _run(steps=[RunStep(order=0, says="a", verdict="held", verdict_by="status")])
    await runs.save(run)

    stale_copy = await runs.get(TENANT, run.id)
    assert stale_copy is not None

    worker_copy = await runs.get(TENANT, run.id)
    assert worker_copy is not None
    worker_copy.steps.append(RunStep(order=1, says="b", verdict="held", verdict_by="status"))
    await runs.save(worker_copy)

    stale_copy.watched = True
    await runs.save(stale_copy)

    back = await runs.get(TENANT, run.id)
    assert back is not None
    assert back.watched is True
    assert [step.order for step in back.steps] == [0, 1]


async def test_saving_again_still_does_not_double_a_step() -> None:
    runs = FakeWorkflowRunRepository()
    run = _run(steps=[RunStep(order=0, says="a", verdict="held", verdict_by="status")])
    await runs.save(run)

    run.steps.append(RunStep(order=1, says="b", verdict="held", verdict_by="status"))
    await runs.save(run)

    back = await runs.get(TENANT, run.id)
    assert back is not None
    assert [step.order for step in back.steps] == [0, 1]
