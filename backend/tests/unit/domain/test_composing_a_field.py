from dataclasses import replace

from sro.domain.execution.compiled import compile_job
from sro.domain.execution.compose import (
    Adding,
    Composed,
    choices,
    compose,
    keyed,
    with_field,
)
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
    assert nowhere[0].labels == ("Department (combobox)", "Department (textbox)")


def test_a_credential_or_a_name_a_step_already_fills_is_never_composed() -> None:
    job, by_id = _job(OutlineField("textbox", "Password"), OutlineField("textbox", "Customer Type"))
    job.steps[0].parameters = ["Customer Type"]

    assert compose(job, by_id, {"Password": "hunter2", "Customer Type": "GT2"}) == ((), ())


def test_a_learned_field_whose_step_was_lost_is_composed_again_never_dropped() -> None:
    job, by_id = _job(OutlineField("combobox", "Department"))
    job.parameters = [{"name": "department", "required": False, "body_key": "department"}]

    composed, _ = compose(job, by_id, {"department": "Finance"})

    assert [one.label for one in composed] == ["Department"]


def test_a_new_key_pairs_only_with_the_value_its_control_holds() -> None:
    two = Adding(fresh={"Department": "Finance", "Region": "7"})

    assert keyed({"department": "Finance", "regionId": "7"}, two) == {
        "Department": "department",
        "Region": "regionId",
    }
    assert keyed({"department": "Finance"}, two) == {"Department": "department"}
    assert keyed({}, two) == {}
    assert keyed({}, Adding()) == {}


def test_a_leftover_key_is_never_paired_by_elimination() -> None:
    one = Adding(fresh={"Department": "Finance"})

    assert keyed({"deptId": "3"}, one) is None
    assert keyed({"validateOnly": "true"}, one) is None
    assert keyed({"department": ""}, one) is None
    assert keyed({"department": "Finance"}, Adding(fresh={"Department": ""})) is None
    assert keyed({"a": "Finance", "b": "Finance"}, one) is None


def test_a_select_pairs_by_the_option_value_it_holds_not_its_label() -> None:
    assert keyed({"deptId": "3"}, Adding(fresh={"Department": "3"})) == {"Department": "deptId"}
    assert keyed({"deptId": "Finance"}, Adding(fresh={"Department": "3"})) is None


def test_two_fields_holding_the_same_value_attribute_no_key() -> None:
    same = Adding(fresh={"Department": "North", "Region": "North"})

    assert keyed({"department": "North"}, same) is None


def test_a_learned_key_still_carries_its_fields_value() -> None:
    learned = Adding(known={"department": "Department"}, fresh={"Department": "3"})

    assert keyed({"department": "3"}, learned) == {"Department": "department"}
    assert keyed({"department": "4"}, learned) is None
    assert keyed({"department": "3"}, Adding(known={"department": "Department"})) is None


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
        "body_key": "department",
    }


def test_a_learned_field_step_is_performable_though_nobody_demonstrated_it() -> None:
    job, by_id = _job(OutlineField("combobox", "Department"))
    write = job.steps[0].order

    grown, _ = with_field(
        job, Composed("department", "Department", "combobox", write), key="department", value="F"
    )

    assert compile_job(
        grown, by_id, learned={}, ledger=(), broken=(), values={"department": "F"}
    ).runnable


def test_a_learned_field_its_form_no_longer_shows_is_refused_before_the_run_starts() -> None:
    job, by_id = _job(OutlineField("combobox", "Dept"))
    write = job.steps[0].order
    grown, _ = with_field(
        job, Composed("department", "Department", "combobox", write), key="department", value="F"
    )

    refused = compile_job(
        grown, by_id, learned={}, ledger=(), broken=(), values={"department": "F"}
    )

    assert not refused.runnable
    assert [(one.code, one.step) for one in refused.reasons] == [("field_gone", write)]
    assert [one.says for one in grown.steps if one.order == write] == ["Fill Department"]
    assert compile_job(grown, by_id, learned={}, ledger=(), broken=(), values={}).runnable


def test_a_label_on_the_form_twice_is_offered_told_apart_or_not_at_all() -> None:
    job, by_id = _job(
        OutlineField("combobox", "Department"),
        OutlineField("textbox", "Department"),
        OutlineField("textbox", "Notes"),
        OutlineField("textbox", "Notes"),
    )

    _, (asked,) = compose(job, by_id, {"department": "Finance"})
    offered = choices(job, by_id)

    assert asked.labels == ("Department (combobox)", "Department (textbox)")
    assert offered["Department (textbox)"].role == "textbox"
    assert not any(one.startswith("Notes") for one in offered)


def test_a_choice_two_writes_would_both_answer_to_is_never_offered() -> None:
    job, by_id = _job(OutlineField("textbox", "Notes"))
    save = by_id["ges_save"]
    later = [replace(one, started_at=(one.started_at or 0) + 5) for one in save.requests]
    by_id["ges_save_2"] = replace(save, id="ges_save_2", at=save.at + 5, requests=later)
    job.steps.append(replace(job.steps[0], order=job.steps[0].order + 1, cites=["ges_save_2"]))

    assert not any(one.startswith("Notes") for one in choices(job, by_id))
