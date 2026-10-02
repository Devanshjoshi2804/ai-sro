"""A unique field the system echoes as a number is still named when it clashes.

QA, 2026-10-02: a warehouse equipment type sent voiceCode "93"; Blue Yonder said
"Record already exists" because SFORK holds voice code 93, listed as the NUMBER 93.
The clash went unnamed and the operator was asked which of four values to change.
"""

from __future__ import annotations

import json

from sro.application.ports.http import HttpResponse
from sro.application.runtime.api_lane import _clash
from sro.domain.execution.belts import record_count
from sro.domain.execution.planning import Planned
from sro.domain.shared.prices import Answer

BODY = {
    "voiceCode": "93",
    "vehicleLimit": "2",
    "longDescription": "voice fresh test",
    "vehicleTypeId": "ZWOYBN",
}
LISTED = json.dumps(
    {
        "data": [
            {"vehicleTypeId": "SFORK", "voiceCode": 93, "vehicleLimit": 2},
            {"vehicleTypeId": "COUNT", "voiceCode": 7, "vehicleLimit": 2},
        ]
    }
)


def _planned() -> Planned:
    return Planned(
        "http.send",
        {"method": "POST", "url": "https://wms.example/equipmentTypes", "body": json.dumps(BODY)},
        "proven",
        Answer(),
        filled={
            "voiceCode": "Voice Code",
            "vehicleLimit": "LPN Limit",
            "longDescription": "Description",
            "vehicleTypeId": "Warehouse Equipment Type",
        },
        # What the read-back compares exactly: the echo of voiceCode is a number, so it is not here.
        confirm={"vehicleTypeId": "ZWOYBN", "longDescription": "voice fresh test"},
    )


def test_a_number_and_its_text_are_the_same_value_in_a_listing() -> None:
    assert record_count(LISTED, {"voiceCode": "93"}) == 1
    assert record_count(LISTED, {"vehicleLimit": "2"}) == 2
    assert record_count(LISTED, {"voiceCode": "930"}) == 0


def test_the_clashing_voice_code_is_named_and_a_shared_limit_is_not() -> None:
    said = _clash(HttpResponse(200, {}, LISTED), _planned())

    assert said == "Voice Code 93"
