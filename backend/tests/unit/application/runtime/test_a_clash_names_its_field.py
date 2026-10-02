"""QA 2026-10-01 (run_0cc6f7f6...): Blue Yonder answered 409 "Record already
exists." for a brand-new Warehouse Equipment Type code, because its Voice Code
(7, held by COUNT) is unique. The words name no field; the list of records
does, so the refusal names the field whose value exactly one record holds."""

from __future__ import annotations

import json
from dataclasses import replace

from sro.application.runtime.api_lane import ApiLane
from sro.domain.execution.lanes import StepResult
from sro.domain.execution.workflow_run import refused_names
from tests.unit.application.runtime.test_a_refused_write import _refused_run
from tests.unit.fakes import FakeHttpCaller
from tests.unit.runtime_support import (
    WORKFLOW,
    headers_broker,
    lane_context,
    proven_write_step,
)

LIST = "/api/customer-types"
WRITE = "https://wms.example/api/customer-types"
VALUES = {"Customer Type": "GT2", "Description": "Pet shops"}
JOB = replace(
    WORKFLOW,
    parameters=[
        {"name": "Customer Type", "seen_values": ["GT0", "GT1"]},
        {"name": "Description", "seen_values": ["d0", "d1"]},
    ],
)
EXISTS = (409, '{"message": "Record already exists."}')


async def _saved(*answers: tuple[int, str]) -> StepResult:
    http = FakeHttpCaller()
    for status, text in answers:
        http.answer(status, text)
    step, by_id, ledger = proven_write_step(read_back=LIST, described=("d0", "d1"))
    return await ApiLane(headers_broker({}, http=http)).execute(
        step, VALUES, lane_context(by_id, ledger=ledger, workflow=JOB)
    )


def _rows(*rows: tuple[str, str]) -> str:
    return json.dumps({"data": [{"name": name, "description": said} for name, said in rows]})


async def test_a_refusal_naming_no_field_names_the_one_whose_value_a_record_holds() -> None:
    result = await _saved(
        EXISTS, (200, _rows(("GT7", "Pet shops"), ("GT8", "Vets"), ("GT9", "Vets"))), (404, "")
    )

    assert result.refused
    assert "Description Pet shops is already used" in result.reason
    assert refused_names(JOB, VALUES, result.reason) == ["Description"]


async def test_a_value_many_records_hold_is_not_what_clashed() -> None:
    result = await _saved(
        EXISTS, (200, _rows(("GT7", "Pet shops"), ("GT8", "Pet shops"))), (404, "")
    )

    assert result.refused
    assert "is already used" not in result.reason


async def test_the_step_keeps_the_call_it_sent_and_no_header() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    step, by_id, ledger = proven_write_step(read_back=None)

    result = await ApiLane(
        headers_broker({"cookie": "sid=1", "x-csrf-token": "t"}, http=http)
    ).execute(step, {"Customer Type": "GT2"}, lane_context(by_id, ledger=ledger))

    assert result.sent == {
        "kind": "http.send",
        "payload": {"method": "POST", "url": WRITE, "body": json.dumps({"name": "GT2"})},
    }


async def test_a_refused_run_keeps_the_write_it_sent() -> None:
    world, _ = await _refused_run()

    (save,) = [one for one in (await world.saved_run()).steps if one.verdict == "failed"]

    assert save.sent is not None and save.sent["payload"]["method"] == "POST"
