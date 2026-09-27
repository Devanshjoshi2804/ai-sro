from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

from sro.domain.execution.compiled import Compiled, compile_job
from sro.domain.execution.compose import Composed, with_field
from sro.domain.execution.lanes import Broken, Lane
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.observation.gesture import Gesture, Outline, OutlineField, Target
from sro.domain.skill.aliases import JobAlias
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.runtime_support import (
    GMAIL,
    mail_send_step,
    proven_write_step,
    save_step,
    type_then_save_step,
)


def _job(*steps: Step, parameters: Sequence[dict[str, object]] = ()) -> Workflow:
    return Workflow(
        id="wfl_c",
        tenant="acme",
        title="Save",
        narrative="",
        steps=list(steps),
        parameters=list(parameters),
    )


def _codes(compiled: Compiled) -> list[str]:
    return [one.code for one in compiled.reasons]


def _warned(compiled: Compiled) -> list[str]:
    return [one.code for one in compiled.warnings]


def test_a_proven_write_with_a_locator_compiles() -> None:
    step, by_id, ledger = proven_write_step(read_back="/api/customer-types/{name}")
    job = _job(step, parameters=[{"name": "Customer Type", "required": True}])

    got = compile_job(job, by_id, learned={}, ledger=ledger, broken=())

    assert got.runnable and got.reasons == ()
    assert got.view["steps"][0]["lanes"] == ["api", "ui", "sight"]
    assert got.view["steps"][0]["proof"]["read_back"] == "/api/customer-types/GT0"


def test_a_mail_send_step_runs_on_the_tool_lane() -> None:
    step, by_id = mail_send_step()

    got = compile_job(_job(step), by_id, learned={}, ledger=(), broken=())

    assert got.runnable, got.reasons
    assert got.view["steps"][0]["lanes"] == ["tool"]


def test_a_required_parameter_no_step_fills_does_not_compile() -> None:
    step, by_id = save_step()
    job = _job(step, parameters=[{"name": "Department", "required": True}])

    got = compile_job(job, by_id, learned={}, ledger=(), broken=())

    assert not got.runnable and _codes(got) == ["unbound_parameter"]


def test_a_required_parameter_is_filled_by_the_control_a_step_types_under_its_name() -> None:
    """A parameter learned from the typing lives on the job and names the
    control; the run fills it by that name, so it is bound without a step
    listing it."""
    step, by_id = type_then_save_step()
    job = _job(
        replace(step, parameters=[]),
        parameters=[{"name": "Kind", "names": ["Kind", "Customer Type"], "required": True}],
    )

    assert "unbound_parameter" not in _codes(
        compile_job(job, by_id, learned={}, ledger=(), broken=())
    )


def test_an_optional_parameter_no_step_fills_is_not_a_reason() -> None:
    step, by_id = save_step()
    job = _job(step, parameters=[{"name": "Department", "required": False}])

    assert compile_job(job, by_id, learned={}, ledger=(), broken=()).runnable


def test_an_alias_binds_a_required_parameter_to_the_field_a_step_fills() -> None:
    step, by_id, ledger = proven_write_step(read_back=None)
    job = _job(
        step,
        parameters=[
            {"name": "client category", "required": True},
            {"name": "Customer Type", "required": False},
        ],
    )
    alias = JobAlias("Client Category", "Customer Type", "clerk", datetime(2026, 9, 25, tzinfo=UTC))

    assert "unbound_parameter" in _codes(
        compile_job(job, by_id, learned={}, ledger=ledger, broken=())
    )
    got = compile_job(job, by_id, learned={}, ledger=ledger, broken=(), aliases=(alias,))

    assert "unbound_parameter" not in _codes(got)


def test_a_write_with_no_status_it_expects_is_unproven() -> None:
    step, by_id = save_step(status=None)

    assert "unproven_write" in _codes(
        compile_job(_job(step), by_id, learned={}, ledger=(), broken=())
    )


def test_a_ui_step_with_no_recorded_or_learned_locator_does_not_compile() -> None:
    step, by_id = save_step()
    bare = {
        key: replace(g, action=replace(g.action, target=Target(role="button")))
        for key, g in by_id.items()
    }

    assert "no_locator" in _codes(compile_job(_job(step), bare, learned={}, ledger=(), broken=()))
    learned = {step.order: LearnedStep(step.order, "text", "Save", "sight")}
    assert "no_locator" not in _codes(
        compile_job(_job(step), bare, learned=learned, ledger=(), broken=())
    )


def test_a_step_broken_on_every_lane_is_a_warning_and_the_job_stays_runnable() -> None:
    step, by_id, ledger = proven_write_step(read_back=None)
    job = _job(step, parameters=[{"name": "Customer Type", "required": True}])
    every = [Broken(step.order, lane, "f") for lane in (Lane.API, Lane.UI, Lane.SIGHT)]

    got = compile_job(job, by_id, learned={}, ledger=ledger, broken=every)

    assert got.runnable and got.reasons == ()
    assert _warned(got) == ["every_lane_broken"]
    assert _warned(compile_job(job, by_id, learned={}, ledger=ledger, broken=every[:2])) == []


def test_a_failed_write_is_not_proven_by_its_status() -> None:
    step, by_id = save_step(status=400)

    got = compile_job(_job(step), by_id, learned={}, ledger=(), broken=())

    assert not got.runnable and _codes(got) == ["unproven_write"]


def test_a_job_with_no_parameters_that_writes_captured_values_is_warned_not_refused() -> None:
    step, by_id, ledger = proven_write_step(read_back=None)
    fixed = _job(replace(step, parameters=[]))

    got = compile_job(fixed, by_id, learned={}, ledger=ledger, broken=())

    assert got.runnable and _warned(got) == ["fixed_values"]
    assert got.view["warnings"][0]["step"] == step.order
    bound = _job(step, parameters=[{"name": "Customer Type", "required": True}])
    assert _warned(compile_job(bound, by_id, learned={}, ledger=ledger, broken=())) == []


def test_a_mail_read_step_with_only_a_scroll_has_no_lane_as_the_start_says() -> None:
    step, by_id = save_step()
    (gesture,) = by_id.values()
    scrolled = replace(
        gesture,
        url=GMAIL,
        system=GMAIL,
        requests=[],
        action=replace(gesture.action, kind="scroll", target=None),
    )

    got = compile_job(_job(step), {gesture.id: scrolled}, learned={}, ledger=(), broken=())

    assert not got.runnable and _codes(got) == ["no_lane"]


def test_a_step_with_no_evidence_has_no_lane_even_with_a_learned_locator() -> None:
    step, by_id = save_step()
    field = replace(step, order=0, says="Fill Department", cites=[], parameters=["Department"])
    job = _job(field, replace(step, order=1))
    learned = {0: LearnedStep(0, "label", "Department", "composed")}

    assert "no_lane" in _codes(compile_job(job, by_id, learned={}, ledger=(), broken=()))
    assert "no_lane" in _codes(compile_job(job, by_id, learned=learned, ledger=(), broken=()))


def _learned_field(label: str) -> tuple[Workflow, dict[str, Gesture], int]:
    step, by_id = save_step(status=201)
    save = by_id["ges_save"]
    by_id["ges_save"] = replace(
        save,
        action=replace(save.action, outlines=(Outline(fields=(OutlineField("combobox", label),)),)),
    )
    job = _job(step)
    grown, _ = with_field(
        job,
        Composed("department", "Department", "combobox", step.order),
        key="department",
        value="F",
    )
    return grown, by_id, step.order


def test_compile_agrees_with_the_value_aware_start_rule_for_a_learned_field() -> None:
    """X10b's rule, now the compile check's: a learned field step is refused only
    when a value is given for it and its label is gone from the write's latest
    outline; with no value it is passed over; the offer view (no values yet)
    compiles."""
    gone, by_id, field = _learned_field("Dept")

    given = compile_job(gone, by_id, learned={}, ledger=(), broken=(), values={"department": "F"})
    assert not given.runnable
    assert [(one.code, one.step) for one in given.reasons] == [("field_gone", field)]
    assert compile_job(gone, by_id, learned={}, ledger=(), broken=(), values={}).runnable
    assert compile_job(gone, by_id, learned={}, ledger=(), broken=()).runnable
    shown, by_id, _ = _learned_field("Department")
    assert compile_job(
        shown, by_id, learned={}, ledger=(), broken=(), values={"department": "F"}
    ).runnable


def test_a_step_before_the_start_point_is_not_asked_about() -> None:
    """D7's takeover: the steps before `from_step` were done by the operator and
    are never sent, so evidence they no longer have does not stop the run."""
    step, by_id = save_step()
    job = _job(replace(step, order=0, cites=["gone"]), replace(step, order=1))

    assert "no_lane" in _codes(compile_job(job, by_id, learned={}, ledger=(), broken=()))
    assert compile_job(job, by_id, learned={}, ledger=(), broken=(), from_step=1).runnable
