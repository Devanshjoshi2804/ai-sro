from dataclasses import replace

from sro.domain.execution.compose import Adding, Composed, compose, keyed, with_field
from sro.domain.observation.gesture import Gesture, Outline, OutlineField
from sro.domain.skill.workflow import Workflow
from tests.unit.runtime_support import save_step


def _job(*fields: OutlineField) -> tuple[Workflow, dict[str, Gesture]]:
    step, by_id = save_step(status=201)
    save = by_id["ges_save"]
    by_id["ges_save"] = replace(
        save, action=replace(save.action, outlines=(Outline(fields=fields),))
    )
    job = Workflow(
        id="wf_ct", tenant="acme", title="Create Customer Type", narrative="", steps=[step]
    )
    return job, by_id


def test_a_value_the_job_never_filled_is_composed_before_the_write_whose_screen_names_it() -> None:
    job, by_id = _job(
        OutlineField("textbox", "Customer Type *", True),
        OutlineField("combobox", "Department", None, ("Finance", "Operations")),
    )

    composed, unplaced = compose(job, by_id, {"department": "Finance"})

    assert composed == (
        Composed(
            "department", "Department", "combobox", job.steps[0].order, ("Finance", "Operations")
        ),
    )
    assert unplaced == ()
    assert composed[0].action == "select"


def test_a_name_no_field_has_or_two_fields_have_is_asked_never_guessed() -> None:
    job, by_id = _job(OutlineField("combobox", "Department"), OutlineField("textbox", "Department"))

    _, twice = compose(job, by_id, {"Department": "Finance"})
    _, nowhere = compose(job, by_id, {"Cost centre": "CC-9"})

    assert [one.why for one in twice] == ["ambiguous"]
    assert [one.why for one in nowhere] == ["no_field"]
    assert nowhere[0].labels == ("Department",)


def test_a_credential_or_a_name_a_step_already_fills_is_never_composed() -> None:
    job, by_id = _job(OutlineField("textbox", "Password"), OutlineField("textbox", "Customer Type"))
    job.steps[0].parameters = ["Customer Type"]

    assert compose(job, by_id, {"Password": "hunter2", "Customer Type": "GT2"}) == ((), ())


def test_the_new_key_is_found_by_its_value_or_as_the_only_one_left() -> None:
    two = Adding(fresh={"Department": "Finance", "Region": "North"})

    assert keyed({"department": "Finance", "regionId": "7"}, two) == {
        "Department": "department",
        "Region": "regionId",
    }
    assert keyed({"deptId": "3", "regionId": "7"}, two) == {}
    assert keyed({"a": "1", "b": "2", "c": "3"}, two) is None
    assert keyed({"department": "3"}, Adding(known={"department": "Department"})) == {
        "Department": "department"
    }
    assert keyed({}, Adding()) == {}


def test_learning_the_field_puts_its_step_before_the_write_and_keeps_it_optional() -> None:
    job, _ = _job(OutlineField("combobox", "Department"))
    write = job.steps[0].order

    grown, moved = with_field(
        job,
        Composed("department", "Department", "combobox", write),
        key="department",
        value="Finance",
    )

    assert [(one.order, one.parameters, one.cites) for one in grown.steps] == [
        (write, ["department"], []),
        (write + 1, [], ["ges_save"]),
    ]
    assert moved == {write: write + 1}
    assert grown.parameters[-1] == {
        "name": "department",
        "required": False,
        "seen_values": ["Finance"],
        "names": ["Department"],
        "key": "department",
    }
