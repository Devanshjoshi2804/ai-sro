import asyncio
import json
from dataclasses import replace

from sro.application.runtime.api_lane import ApiLane
from sro.application.runtime.executor import StepExecutor
from sro.application.runtime.fill_field import Filled
from sro.domain.execution.compose import Adding, Composed, with_field
from sro.domain.execution.lanes import Lane, StepResult
from sro.domain.observation.gesture import Outline, OutlineField
from tests.unit.domain.test_a_learned_key_is_a_slot import _job
from tests.unit.fakes import FakeHttpCaller
from tests.unit.runtime_support import (
    APP,
    CTX,
    TENANT,
    WORKFLOW,
    FakeBroker,
    RecordingLane,
    headers_broker,
    lane_context,
    never,
    no_tool,
    steel_run,
)

VALUES = {"Customer Type": "GT2", "Department": "Finance"}
LIST = "/api/customer-types"


def _as_fill_for_builds_it(*composed: str) -> Adding:
    return Adding(
        known={"department": "Department"},
        fresh={"Department": "Finance", **dict.fromkeys(composed, "x")},
    )


async def _first_lane(adding: Adding, body_key: str | None) -> Lane:
    job, write, by_id, ledger = _job(body_key)
    api = RecordingLane(Lane.API, StepResult("done", Lane.API))
    ui = RecordingLane(Lane.UI, StepResult("done", Lane.UI))
    ctx = lane_context(by_id, ledger=ledger, adding={write.order: adding}, workflow=job)

    tried = await StepExecutor(no_tool(), api, ui, never(), FakeBroker()).run(
        write, VALUES, ctx, broken=(), start_url=""
    )
    return tried[0].lane


async def test_a_field_learned_with_its_key_lets_the_write_go_through_the_api_lane() -> None:
    assert await _first_lane(_as_fill_for_builds_it(), "department") is Lane.API


async def test_a_field_composed_this_run_keeps_the_api_lane_closed() -> None:
    assert await _first_lane(Adding(fresh={"Department": "Finance"}), None) is Lane.UI


async def test_a_field_composed_beside_a_learned_one_keeps_the_api_lane_closed() -> None:
    assert await _first_lane(_as_fill_for_builds_it("Region"), "department") is Lane.UI


async def test_a_learned_field_whose_slot_was_removed_keeps_the_api_lane_closed() -> None:
    assert await _first_lane(_as_fill_for_builds_it(), None) is Lane.UI


async def _api_write(read_back: dict[str, object]) -> StepResult:
    job, write, by_id, ledger = _job("department", read_back=LIST)
    http = FakeHttpCaller()
    http.answer(201, '{"id": "ct-9"}')
    http.answer(200, json.dumps(read_back))
    ctx = lane_context(
        by_id, ledger=ledger, adding={write.order: _as_fill_for_builds_it()}, workflow=job
    )
    result = await ApiLane(http, headers_broker({"cookie": "sid=1"})).execute(write, VALUES, ctx)
    assert json.loads(str(http.sent[0]["body"])) == {"name": "GT2", "department": "Finance"}
    return result


async def test_an_api_write_whose_read_back_shows_the_learned_field_keys_it() -> None:
    result = await _api_write({"name": "GT2", "department": "Finance"})
    assert result.verdict == "done"
    assert dict(result.keyed) == {"Department": "department"}


async def test_an_api_write_whose_read_back_lacks_the_learned_field_keys_nothing() -> None:
    result = await _api_write({"name": "GT2", "department": None})
    assert result.verdict == "unknown"
    assert dict(result.keyed) == {}


async def test_an_in_doubt_api_write_settled_by_its_read_back_keys_the_learned_field() -> None:
    job, write, by_id, ledger = _job("department", read_back=LIST)
    lost = StepResult("unknown", Lane.API, "sent to sign in", expired=True)
    api = RecordingLane(Lane.API, lost, settles="done")
    ctx = lane_context(
        by_id, ledger=ledger, adding={write.order: _as_fill_for_builds_it()}, workflow=job
    )

    tried = await StepExecutor(no_tool(), api, never(), never(), FakeBroker()).run(
        write, VALUES, ctx, broken=(), start_url=APP
    )

    assert [one.verdict for one in tried] == ["done"]
    assert dict(tried[-1].keyed) == {"Department": "department"}


async def test_a_run_writes_a_slotted_learned_field_through_the_api_lane_and_holds() -> None:
    _, write, by_id, _ = _job("department", read_back=LIST)
    shown = Outline(fields=(OutlineField("combobox", "Department", None, ("Finance", "Sales")),))
    by_id = {
        key: replace(one, action=replace(one.action, outlines=(shown,)))
        for key, one in by_id.items()
    }
    job, _ = with_field(
        replace(WORKFLOW, steps=[replace(write, order=0)]),
        Composed("Department", "Department", "combobox", 0, ("Finance", "Sales")),
        key="department",
        value="Finance",
    )
    http = FakeHttpCaller()
    http.answer(201, '{"id": "ct-9"}')
    http.answer(200, json.dumps({"name": "GT2", "department": "Finance"}))
    world = await steel_run(steps=[(write, by_id)], job=job, values=VALUES, http=http)
    world.uow.workflows.learned_write_rows[(TENANT.value, "POST", "/api/customer-types")] = {}
    world.fill.answers(Filled(Lane.UI, held="Finance"))
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)

    for _ in range(2):
        await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    outcome = await world.run_steps.finish(CTX, world.run_id)

    assert [one["method"] for one in http.sent] == ["POST", "GET"]
    assert json.loads(str(http.sent[0]["body"])) == {"name": "GT2", "department": "Finance"}
    assert world.lanes.ui.calls == 0
    rows = [(one.says, one.verdict, one.verdict_by) for one in (await world.saved_run()).steps]
    assert ("Fill Department", "held", "ui") in rows
    assert outcome == "held"
