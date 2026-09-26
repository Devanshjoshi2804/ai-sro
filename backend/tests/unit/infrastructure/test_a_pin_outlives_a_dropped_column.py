"""A run's pin is the job's rows as they stood when it started. A later
migration can drop a column from `workflows` or `workflow_steps`; a pin
stored before it still carries that key, and must still load."""

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
