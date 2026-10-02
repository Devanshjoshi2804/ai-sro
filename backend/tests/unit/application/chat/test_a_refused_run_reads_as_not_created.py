"""QA 2026-10-02: the brain said a warehouse equipment type "already exists" because the run
for it was refused over the VOICE CODE. A refused run made nothing; the brain's evidence says so."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from sro.application.chat.brain_tools import RunStatus
from sro.application.chat.read_threads import ReadThreads
from sro.application.execution.workflow_runs import ListWorkflowRuns
from sro.domain.execution.workflow_run import RunStep
from tests.unit.application.runtime.test_a_refused_write import _refused_run
from tests.unit.runtime_support import CTX


async def _rows(world: Any) -> list[dict[str, Any]]:
    result = await RunStatus(ListWorkflowRuns(world.uow), ReadThreads(world.uow)).run(CTX, {})
    return list(result.data["runs"])  # type: ignore[call-overload]


async def test_a_run_the_lane_refused_reads_as_not_created_through_the_real_step_path() -> None:
    world, _ = await _refused_run()

    (one,) = await _rows(world)

    assert (
        one["state"] == "not created: the system refused it (Description Pet shops is already used)"
    )
    assert one["stopped_because"] == ""


async def test_the_state_does_not_say_the_system_refused_it_twice() -> None:
    world, _ = await _refused_run()
    run = await world.saved_run()
    reason = "the system refused it: Record already exists. Voice Code 7 is already used"
    run.steps = [replace(one, reason=reason) for one in run.steps]
    await world.uow.workflow_runs.save(run)

    (one,) = await _rows(world)

    assert one["state"] == (
        "not created: the system refused it (Record already exists. Voice Code 7 is already used)"
    )


async def test_a_run_the_rig_refused_is_not_said_to_have_made_nothing() -> None:
    world, _ = await _refused_run()
    run = await world.saved_run()
    run.outcome = "refused"
    run.steps = [replace(one, result=None, reason="over the item cap") for one in run.steps]
    run.steps.append(RunStep(order=99, says="x", verdict="failed", reason="over the item cap"))
    await world.uow.workflow_runs.save(run)

    (one,) = await _rows(world)

    assert "not created" not in str(one["state"])
    assert one["stopped_because"] == "over the item cap"
