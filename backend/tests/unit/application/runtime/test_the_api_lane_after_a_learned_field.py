from sro.application.runtime.executor import StepExecutor
from sro.domain.execution.compose import Adding
from sro.domain.execution.lanes import Lane, StepResult
from tests.unit.domain.test_a_learned_key_is_a_slot import _job
from tests.unit.runtime_support import FakeBroker, RecordingLane, lane_context, never, no_tool


async def _first_lane(adding: Adding, body_key: str | None) -> Lane:
    job, write, by_id, ledger = _job(body_key)
    api = RecordingLane(Lane.API, StepResult("done", Lane.API))
    ui = RecordingLane(Lane.UI, StepResult("done", Lane.UI))
    ctx = lane_context(by_id, ledger=ledger, adding={write.order: adding}, workflow=job)

    tried = await StepExecutor(no_tool(), api, ui, never(), FakeBroker()).run(
        write, {"Customer Type": "GT2", "Department": "Finance"}, ctx, broken=(), start_url=""
    )
    return tried[0].lane


async def test_a_field_learned_with_its_key_lets_the_write_go_through_the_api_lane() -> None:
    assert await _first_lane(Adding(known={"department": "Department"}), "department") is Lane.API


async def test_a_field_composed_this_run_keeps_the_api_lane_closed() -> None:
    assert await _first_lane(Adding(fresh={"Department": "Finance"}), None) is Lane.UI


async def test_a_learned_field_whose_slot_was_removed_keeps_the_api_lane_closed() -> None:
    assert await _first_lane(Adding(known={"department": "Department"}), None) is Lane.UI
