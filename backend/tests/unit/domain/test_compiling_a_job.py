from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

from sro.domain.execution.compiled import Compiled, compile_job
from sro.domain.execution.lanes import Broken, Lane
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.observation.gesture import Target
from sro.domain.skill.aliases import JobAlias
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.runtime_support import mail_send_step, proven_write_step, save_step


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


def test_a_step_broken_on_every_lane_does_not_compile_and_one_live_lane_is_enough() -> None:
    step, by_id, ledger = proven_write_step(read_back=None)
    every = [Broken(step.order, lane, "f") for lane in (Lane.API, Lane.UI, Lane.SIGHT)]

    assert "every_lane_broken" in _codes(
        compile_job(_job(step), by_id, learned={}, ledger=ledger, broken=every)
    )
    assert "every_lane_broken" not in _codes(
        compile_job(_job(step), by_id, learned={}, ledger=ledger, broken=every[:2])
    )


def test_a_step_with_no_evidence_has_no_lane_even_with_a_learned_locator() -> None:
    step, by_id = save_step()
    field = replace(step, order=0, says="Fill Department", cites=[], parameters=["Department"])
    job = _job(field, replace(step, order=1))
    learned = {0: LearnedStep(0, "label", "Department", "composed")}

    assert "no_lane" in _codes(compile_job(job, by_id, learned={}, ledger=(), broken=()))
    assert "no_lane" in _codes(compile_job(job, by_id, learned=learned, ledger=(), broken=()))
