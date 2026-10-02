"""A step keeps the call it sent (never a header: those carry the session), also
when the write was refused. (QA 2026-10-01 had Blue Yonder answer 409 "Record
already exists." for a Warehouse Equipment Type; inferring the clashing field
from the list of records was removed 2026-10-02: the record had landed, and a
guessed field invites a second record. See test_a_landed_write_is_never_refused.)"""

from __future__ import annotations

import json

from sro.application.runtime.api_lane import ApiLane
from tests.unit.application.runtime.test_a_refused_write import _refused_run
from tests.unit.fakes import FakeHttpCaller
from tests.unit.runtime_support import (
    headers_broker,
    lane_context,
    proven_write_step,
)

WRITE = "https://wms.example/api/customer-types"


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
