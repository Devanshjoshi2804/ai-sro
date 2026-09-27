"""A run's pin is the job's rows as they stood when it started. A later
migration can drop a column from `workflows` or `workflow_steps`; a pin
stored before it still carries that key, and must still load."""

from sro.domain.skill.tabs import MAIN, unresolved
from sro.domain.skill.workflow import Step, Workflow
from sro.infrastructure.db.workflows import workflow_from_json, workflow_json

JOB = Workflow(
    id="wfl_1",
    tenant="acme",
    title="save it",
    narrative="",
    steps=[Step(order=0, says="save it", system=None, cites=["ges_1"])],
    parameters=[{"name": "who"}],
)


def test_a_pin_with_a_column_since_dropped_still_loads() -> None:
    stored = workflow_json(JOB)
    stored["workflow"]["dropped_since"] = "x"
    stored["steps"][0]["dropped_since"] = 1

    assert workflow_from_json(stored) == JOB


def test_a_pin_from_before_steps_knew_their_tab_reads_as_main() -> None:
    """A run pinned before 0086 has no `tab` on its steps: undecided, read as main."""
    stored = workflow_json(JOB)
    del stored["steps"][0]["tab"]

    back = workflow_from_json(stored)

    assert back.steps[0].tab is None and back.steps[0].role == MAIN
    assert unresolved(back.steps) == []


def test_a_step_row_leaves_its_tab_to_the_caller() -> None:
    """No Python-side default: an insert that names no tab (a migration test
    seeding a schema older than 0086) must not send the column."""
    from sqlalchemy import insert

    from sro.infrastructure.db.models import WorkflowStepRow

    sent = insert(WorkflowStepRow.__table__).values(workflow_id="wfl_1", ord=0).compile()

    assert "tab" not in sent.params
    assert WorkflowStepRow.__table__.c.tab.nullable
