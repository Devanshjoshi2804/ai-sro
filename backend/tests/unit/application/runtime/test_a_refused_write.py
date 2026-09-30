"""A write Blue Yonder did not accept keeps what it answered, is settled by
reading its record back, and a refusal is asked about where the job came from.

Seen on QA 2026-09-30 (tenant greyorange): "create Warehouse Equipment Type
PJ26, Voice Code 42" -- 42 already belonged to REACH1, Blue Yonder refused the
save, and the run's step ended unclear, "'Click the save button.' was sent and
nothing confirms it; check it and answer", keeping nothing of the answer.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace

from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.fakes import FakeHttpCaller
from tests.unit.runtime_support import CTX, TENANT, WORKFLOW, SteelRun, proven_write_step, steel_run

VALUES = {"Customer Type": "GT2", "Description": "Pet shops"}

REFUSED = json.dumps({"errors": [{"message": "Description Pet shops is already used"}]})


def _job() -> tuple[Workflow, tuple[Step, dict[str, Gesture]]]:
    save, saved, _ = proven_write_step(read_back=None, described=("d0", "d1"))
    job = replace(
        WORKFLOW,
        steps=[replace(save, order=0)],
        parameters=[
            {"name": "Customer Type", "seen_values": ["GT0", "GT1"]},
            {"name": "Description", "seen_values": ["d0", "d1"]},
        ],
    )
    return job, (replace(save, order=0), saved)


async def _saving(*answers: tuple[int, str]) -> tuple[SteelRun, FakeHttpCaller]:
    job, step = _job()
    http = FakeHttpCaller()
    for status, text in answers:
        http.answer(status, text, headers={"content-type": "application/json"})
    world = await steel_run(steps=[step], job=job, values=VALUES, http=http)
    await world.uow.workflows.remember_write(
        TENANT,
        method="POST",
        path_pattern="/api/customer-types",
        origin="https://wms.example",
        run_id="run_proof",
        workflow_id=job.id,
        verified_by="status",
        at="2026-09-21T18:36:07+00:00",
    )
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    return world, http


async def test_a_save_answered_with_a_server_error_keeps_the_status_and_what_it_said() -> None:
    world, _ = await _saving((502, '{"message": "upstream timed out"}'))

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    last = (await world.saved_run()).steps[-1]
    assert last.result is not None
    assert last.result["status"] == "502"
    assert last.result["said"] == "upstream timed out"


async def test_a_clash_whose_record_is_absent_fails_in_its_own_words_and_is_not_redone() -> None:
    world, http = await _saving((409, REFUSED), (404, ""))

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    last = (await world.saved_run()).steps[-1]
    assert last.verdict == "failed", "a refusal the system can read back is not unclear"
    assert "Description Pet shops is already used" in last.reason
    assert "nothing confirms it" not in last.reason
    assert world.lanes.ui.calls == 0, "a refused value was handed to another lane"
    assert [one["method"] for one in http.sent] == ["POST", "GET"]
