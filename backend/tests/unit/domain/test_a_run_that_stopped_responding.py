"""When a `running` row is stuck: its time is up, or its durable workflow is gone.

The whole rule lives in `domain/execution/waiting.stuck`, so the sweep and
anything else that asks agree. A run waiting on a person is never stuck by
time; a Steel run whose workflow Temporal says is closed is stuck whatever it
was waiting on, because nothing is left to take the answer.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sro.domain.execution.progress import K_BUDGET_MARGIN_S
from sro.domain.execution.waiting import STUCK, stuck
from sro.domain.execution.workflow_run import RunStep, WorkflowRun, end_the_steps

STARTED = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
BUDGET = 120.0
UP = STARTED + timedelta(seconds=BUDGET + K_BUDGET_MARGIN_S)


def _run(**overrides: object) -> WorkflowRun:
    run = WorkflowRun(
        id="run_a",
        tenant="acme",
        workflow_id="wfl_1",
        device_id="dev_1",
        values={},
        started_by="clerk",
        live=True,
        allow_focus=False,
        started_at=STARTED.isoformat(),
    )
    for name, value in overrides.items():
        setattr(run, name, value)
    return run


def test_a_run_is_stuck_once_its_budget_and_margin_have_passed() -> None:
    run = _run()

    assert not stuck(run, budget_s=BUDGET, now=UP - timedelta(seconds=1), durable="unknown")
    assert stuck(run, budget_s=BUDGET, now=UP, durable="unknown")


def test_a_run_of_several_things_has_the_budget_once_per_thing() -> None:
    run = _run(items=[{"clientCode": "A"}, {"clientCode": "B"}])

    assert not stuck(run, budget_s=BUDGET, now=UP, durable="unknown")
    assert stuck(run, budget_s=BUDGET, now=UP + timedelta(seconds=BUDGET), durable="unknown")


def test_an_ended_run_is_never_stuck() -> None:
    for outcome in ("held", "failed", "stopped", "aborted", "refused"):
        assert not stuck(_run(outcome=outcome), budget_s=BUDGET, now=UP, durable="closed")


def test_a_run_waiting_for_an_approval_is_not_stuck_by_time() -> None:
    waiting = _run(steps=[RunStep(order=0, says="save", verdict="awaiting")])

    assert not stuck(waiting, budget_s=BUDGET, now=UP + timedelta(days=1), durable="unknown")


def test_a_run_waiting_on_a_question_is_not_stuck_by_time() -> None:
    asking = _run(progress={"asking": {"id": "q-1", "kind": "step", "text": "done?"}})

    assert not stuck(asking, budget_s=BUDGET, now=UP + timedelta(days=1), durable="unknown")


def test_a_run_whose_workflow_is_still_open_is_not_stuck() -> None:
    assert not stuck(_run(), budget_s=BUDGET, now=UP + timedelta(days=1), durable="open")


def test_a_run_whose_workflow_closed_is_stuck_at_once_even_while_it_asks() -> None:
    asking = _run(progress={"asking": {"id": "q-1", "kind": "code", "text": "the code?"}})

    assert stuck(asking, budget_s=BUDGET, now=STARTED, durable="closed")


def test_a_step_that_finished_keeps_its_verdict_and_the_run_resumes_after_it() -> None:
    """`begins_again_at` restarts at the last step's order: marking a finished
    write failed would perform that write a second time."""
    steps = [
        RunStep(order=0, says="open", verdict="done"),
        RunStep(order=1, says="save", verdict="done"),
    ]

    end_the_steps(steps, STUCK)

    assert [(one.order, one.verdict) for one in steps] == [(0, "done"), (1, "done"), (2, "failed")]
    assert steps[-1].reason == STUCK


def test_a_step_that_never_finished_takes_the_reason_itself() -> None:
    steps = [
        RunStep(order=0, says="open", verdict="done"),
        RunStep(order=1, says="save", verdict="held"),
    ]

    end_the_steps(steps, STUCK)

    assert [(one.order, one.verdict, one.reason) for one in steps] == [
        (0, "done", ""),
        (1, "failed", STUCK),
    ]
