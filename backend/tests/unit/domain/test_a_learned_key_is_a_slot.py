import json
from collections.abc import Mapping
from dataclasses import replace

from sro.domain.execution.compose import with_slots, without_slots
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.execution.write_plan import learned_slots, seen_values, write_plan_for
from sro.domain.observation.gesture import Body, Call, Gesture
from sro.domain.skill.workflow import Step, Workflow, field_key
from tests.unit.runtime_support import proven_write_step


def _answered(by_id: Mapping[str, Gesture]) -> dict[str, Gesture]:
    def with_response(call: Call) -> Call:
        if call.method != "POST" or call.request_body is None or call.request_body.text is None:
            return call
        name = json.loads(call.request_body.text)["name"]
        record = {"name": name, "department": None}
        return replace(
            call, response_body=Body(text=json.dumps(record), mime_type="application/json")
        )

    return {
        k: replace(g, requests=[with_response(c) for c in g.requests]) for k, g in by_id.items()
    }


def _job(
    body_key: str | None,
) -> tuple[Workflow, Step, dict[str, Gesture], tuple[VerifiedWrite, ...]]:
    write, by_id, ledger = proven_write_step(read_back=None)
    field = Step(order=0, says="Fill Department", system=write.system, parameters=["Department"])
    write = replace(write, order=1)
    department: dict[str, object] = {
        "name": "Department",
        "required": False,
        "seen_values": ["Finance"],
        "names": ["Department"],
    }
    if body_key:
        department["body_key"] = body_key
    job = Workflow(
        id="wfl_k",
        tenant="acme",
        title="Save",
        narrative="",
        steps=[field, write],
        parameters=[{"name": "Customer Type", "seen_values": ["GT0", "GT1"]}, department],
    )
    return job, write, _answered(by_id), ledger


def test_a_learned_key_is_a_slot_of_the_write_after_its_field() -> None:
    job, write, _, _ = _job("department")
    assert learned_slots(job, write) == {"Department": "department"}
    assert learned_slots(job, job.steps[0]) == {}


def test_the_write_carries_the_learned_key_and_its_read_back_checks_it() -> None:
    job, write, by_id, ledger = _job("department")
    values = {"Customer Type": "GT2", "Department": "Finance"}

    plan = write_plan_for(
        write, by_id, values, ledger, seen_values(job), learned=learned_slots(job, write)
    )

    assert plan is not None
    assert json.loads(plan.body or "") == {"name": "GT2", "department": "Finance"}
    assert plan.confirm["department"] == "Finance"


def test_with_no_learned_key_a_value_the_write_cannot_carry_leaves_no_plan() -> None:
    job, write, by_id, ledger = _job(None)
    plan = write_plan_for(
        write,
        by_id,
        {"Customer Type": "GT2", "Department": "Finance"},
        ledger,
        seen_values(job),
        learned=learned_slots(job, write),
    )
    assert plan is None


def test_a_learned_key_the_recorded_response_never_names_is_no_slot() -> None:
    job, write, _, ledger = _job("department")
    _, bare, _ = proven_write_step(read_back=None)
    plan = write_plan_for(
        write,
        bare,
        {"Customer Type": "GT2", "Department": "Finance"},
        ledger,
        seen_values(job),
        learned=learned_slots(job, write),
    )
    assert plan is None


def test_a_slot_is_removed_and_put_back() -> None:
    job, write, _, _ = _job("department")
    bare = without_slots(job, ["Department"])
    assert bare is not None and learned_slots(bare, write) == {}
    assert without_slots(bare, ["Department"]) is None
    again = with_slots(bare, {"Department": "department"})
    assert again is not None and learned_slots(again, write) == {"Department": "department"}
    assert with_slots(again, {"Department": "department"}) is None


def test_a_removed_slot_leaves_the_field_a_field() -> None:
    job, _, _, _ = _job("department")
    bare = without_slots(job, ["Department"])
    assert bare is not None and field_key(bare, bare.steps[0]) == "department"


def test_only_a_learned_field_takes_a_slot() -> None:
    job, _, _, _ = _job("department")
    assert with_slots(job, {"Customer Type": "name"}) is None
