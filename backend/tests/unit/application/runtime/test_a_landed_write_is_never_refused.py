"""QA 2026-10-02 (runs run_dac421e9..., run_5fcefc71...): "Create a Warehouse
Equipment Type" sent one POST to /equipmentTypes; Blue Yonder answered 409
"Record already exists." and a lookup right after said the type exists. It
had landed. The run called it refused because its read-back looked in the wrong
places: the recording's confirming read was a different collection
(warehouseEquipmentAccesses), and GET /equipmentTypes/<code> answers 404 --
the record's address is not its code. A landed write is never refused, and a
409 whose read-back cannot find the record is in doubt, never a value question.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from sro.application.ports.http import HttpResponse
from sro.application.runtime.api_lane import ApiLane
from sro.domain.execution.lanes import StepResult
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.observation.gesture import Action, Body, Call, Gesture, Target
from sro.domain.skill.workflow import Step
from tests.unit.runtime_support import WORKFLOW, headers_broker, lane_context

ORIGIN = "https://bf56-kms-wms-web-np2.jdadelivers.com"
SITE = f"{ORIGIN}/data/WM/wm"
QUERY = "?siteId=SG&subsites=----&subsites=TESTSRO&_dc=1789619180876"
TYPES = f"{SITE}/equipmentTypes{QUERY}"
ACCESSES = f"{SITE}/warehouseEquipmentAccesses{QUERY}"
JOB = WORKFLOW.__class__(
    id=WORKFLOW.id,
    tenant=WORKFLOW.tenant,
    title="Create a Warehouse Equipment Type",
    narrative="",
    parameters=[
        {"name": "Warehouse Equipment Type", "seen_values": ["ZWA", "ZWB"]},
        {"name": "Description", "seen_values": ["first", "second"]},
        {"name": "Voice Code", "seen_values": ["1", "2"]},
        {"name": "LPN Limit", "seen_values": ["3", "4"]},
    ],
)
VALUES = {
    "Warehouse Equipment Type": "ZWOYBN",
    "Description": "voice fresh test",
    "Voice Code": "93",
    "LPN Limit": "2",
}
SENT = {
    "voiceCode": "93",
    "vehicleLimit": "2",
    "longDescription": "voice fresh test",
    "vehicleTypeId": "ZWOYBN",
    "location": 0,
    "captureEquipment": False,
    "useWorkAreaMove": False,
}
EXISTS = HttpResponse(409, {}, '{"message": "Record already exists."}')
MINE = {
    "vehicleTypeId": "ZWOYBN",
    "longDescription": "voice fresh test",
    "voiceCode": 93,
    "vehicleLimit": 2,
    "resourceId": "ZWOYBN*!7",
}


def _call(method: str, url: str, at: float, sent: Mapping[str, object] | None, back: str) -> Call:
    return Call(
        method=method,
        url=url,
        status=201 if method == "POST" else 200,
        started_at=at,
        request_headers={"Content-Type": "application/json"} if sent else {},
        request_body=Body(text=json.dumps(sent), mime_type="application/json") if sent else None,
        response_body=Body(text=back, mime_type="application/json"),
    )


def _recorded() -> tuple[Step, dict[str, Gesture]]:
    by_id: dict[str, Gesture] = {}
    for nth, (code, said, voice, limit) in enumerate(
        (("ZWA", "first", 1, 3), ("ZWB", "second", 2, 4))
    ):
        at = float(nth + 1)
        body = {"voiceCode": str(voice), "vehicleLimit": str(limit), "longDescription": said,
                "vehicleTypeId": code, "location": 0, "captureEquipment": False,
                "useWorkAreaMove": False}  # fmt: skip
        echoed = {**body, "voiceCode": voice, "vehicleLimit": limit}
        by_id[f"ges_{nth}"] = Gesture(
            id=f"ges_{nth}", tenant=WORKFLOW.tenant, stream_id="s", batch_id="b", at=at,
            url=ORIGIN, system=ORIGIN, tab_id=1, frame_url=None,
            action=Action(kind="click", at=at, target=Target(role="button", name="Save")),
            requests=[
                _call("POST", TYPES, at, body, json.dumps(echoed)),
                _call("GET", ACCESSES, at + 0.5, None, '{"data": [{"vehicleType": "X"}]}'),
            ],
        )  # fmt: skip
    step = Step(order=1, says="Save", system=ORIGIN, cites=list(by_id), parameters=list(VALUES))
    return step, by_id


class _By:
    """Blue Yonder as seen on QA: the collection lists, the code's own address 404s."""

    def __init__(self, write: HttpResponse, listed: list[dict[str, object]]) -> None:
        self.write, self.listed = write, listed
        self.reads: list[str] = []

    async def send(self, method: str, url: str, **_: object) -> HttpResponse:
        if method == "POST":
            return self.write
        self.reads.append(url)
        path = url.split("?")[0]
        if path.endswith("/equipmentTypes"):
            return HttpResponse(
                200, {}, json.dumps({"@type": "ResponseBodyWrapper", "data": self.listed})
            )
        if path.endswith("/warehouseEquipmentAccesses"):
            return HttpResponse(200, {}, json.dumps({"data": [{"vehicleType": "7BHAND"}]}))
        return HttpResponse(404, {}, '{"message": "Not found"}')


async def _saved(write: HttpResponse, listed: list[dict[str, object]]) -> tuple[StepResult, _By]:
    step, by_id = _recorded()
    by = _By(write, listed)
    ledger = (VerifiedWrite("POST", "/data/WM/wm/equipmentTypes"),)
    result = await ApiLane(headers_broker({}, http=by)).execute(
        step, VALUES, lane_context(by_id, ledger=ledger, workflow=JOB)
    )
    return result, by


async def test_a_409_whose_record_the_collection_lists_landed() -> None:
    result, by = await _saved(EXISTS, [{"vehicleTypeId": "OLD", "voiceCode": 7}, MINE])

    assert result.verdict == "done" and not result.refused
    assert result.sent is not None
    assert any(url.split("?")[0].endswith("/equipmentTypes") for url in by.reads)


async def test_a_201_whose_record_the_collection_lists_is_done() -> None:
    result, _ = await _saved(HttpResponse(201, {}, json.dumps(MINE)), [MINE])

    assert result.verdict == "done"


async def test_a_409_whose_record_is_not_found_is_in_doubt_not_a_value_question() -> None:
    result, _ = await _saved(EXISTS, [{"vehicleTypeId": "OLD", "voiceCode": 93}])

    assert result.verdict == "unknown" and not result.refused


async def test_a_409_over_a_record_holding_other_values_is_still_refused() -> None:
    other = {**MINE, "longDescription": "someone else's"}
    result, _ = await _saved(EXISTS, [other])

    assert result.refused and "ZWOYBN" in result.reason
