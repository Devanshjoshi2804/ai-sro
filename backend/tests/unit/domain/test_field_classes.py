from dataclasses import replace

from sro.domain.execution.field_classes import FieldLimits, field_classes
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.observation.gesture import Gesture, Outline, OutlineField
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.runtime_support import type_then_save_step

OUTLINE = Outline(
    fields=(
        OutlineField("textbox", "Customer Type", required=True),
        OutlineField("combobox", "Department", options=("Finance", "Operations")),
        OutlineField("textbox", "Password"),
    )
)


def _job(
    parameters: list[dict[str, object]],
) -> tuple[Workflow, dict[str, Gesture], Step]:
    step, by_id = type_then_save_step()
    by_id = {k: replace(g, action=replace(g.action, outlines=(OUTLINE,))) for k, g in by_id.items()}
    return (
        Workflow(
            id="wfl_f",
            tenant="acme",
            title="Save",
            narrative="",
            steps=[step],
            parameters=parameters,
        ),
        by_id,
        step,
    )


def test_each_field_gets_its_class_from_the_evidence() -> None:
    job, by_id, _ = _job(
        [
            {"name": "Customer Type", "required": True},
            {"name": "Note", "required": False, "in_all": True},
            {"name": "Region", "required": False, "in_all": False},
        ]
    )

    got = {one.name: one.kind for one in field_classes(job, by_id, {})}

    assert got == {
        "Customer Type": "required",
        "Note": "always",
        "Region": "sometimes",
        "Department": "never",
    }


def test_limits_come_from_the_page_and_what_a_field_held() -> None:
    job, by_id, step = _job([{"name": "Customer Type", "required": True}])
    learned = {step.order: LearnedStep(step.order, "text", "x", "sight", holds=4)}

    got = {one.name: one.limits for one in field_classes(job, by_id, learned)}

    assert got["Customer Type"] == FieldLimits(max_length=4, options=None, required_on_screen=True)
    assert got["Department"].options == ("Finance", "Operations")


def test_a_value_that_cannot_fit_is_refused_with_its_reason() -> None:
    assert FieldLimits(max_length=3).refuses("GT10") == "longer than 3 characters"
    assert FieldLimits(options=("Finance",)).refuses("finance ") == ""
    assert FieldLimits(options=("Finance",)).refuses("Ops").startswith("not one of")


def test_the_stricter_of_page_and_knowledge_base_limit_wins() -> None:
    job, by_id, _ = _job([{"name": "Customer Type", "required": True}])
    declared = {"Customer Type": 4}

    got = {one.name: one.limits for one in field_classes(job, by_id, {}, declared)}

    assert got["Customer Type"].max_length == 4
    assert got["Customer Type"].refuses("ZZAUD") == "longer than 4 characters"


def test_a_knowledge_base_only_limit_is_still_enforced_even_when_the_page_is_looser() -> None:
    job, by_id, step = _job([{"name": "Customer Type", "required": True}])
    learned = {step.order: LearnedStep(step.order, "text", "x", "sight", holds=60)}
    declared = {"Customer Type": 4}

    got = {one.name: one.limits for one in field_classes(job, by_id, learned, declared)}

    assert got["Customer Type"].max_length == 4
