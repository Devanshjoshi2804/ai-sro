"""What a proven workflow is, and where it lives."""

import json
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from rig.store import Store


def new_workflow_id() -> str:
    return "wfl_" + secrets.token_hex(16)


@dataclass
class Step:
    order: int
    says: str
    system: str | None
    # Every step cites the gestures that prove it. Free-generated workflow JSON
    # hallucinated up to 21% of steps; forced to select from real evidence, that
    # fell below 7.5%. An uncited step is a rejected step -- see checks.py.
    cites: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)


@dataclass
class Workflow:
    id: str
    tenant: str
    title: str
    narrative: str
    systems: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    parameters: list[dict[str, Any]] = field(default_factory=list)
    shape_key: list[list[str]] = field(default_factory=list)
    # The model's opinion about whether this is one it has proposed before. It is
    # recorded and it decides nothing: a model re-judging its own earlier verdict
    # disagrees with itself at roughly 90%. identity.py decides.
    same_as: str | None = None
    unproven: list[str] = field(default_factory=list)
    # The pass that found it. A workflow has no cost of its own -- one model
    # call proposes all of them -- so it names the row that does rather than
    # carrying a copy of the bill that three workflows would then sum to three
    # times. Empty for a workflow saved outside a pass, which today is only a
    # test.
    pass_id: str = ""


def cited_ids(workflow: Workflow) -> set[str]:
    return {gesture_id for step in workflow.steps for gesture_id in step.cites}


def save_workflow(store: Store, workflow: Workflow) -> None:
    with store.connect() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO workflows (id, tenant, pass_id, title, narrative,"
            " systems, parameters, shape_key, same_as, unproven, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                workflow.id,
                workflow.tenant,
                workflow.pass_id,
                workflow.title,
                workflow.narrative,
                json.dumps(workflow.systems),
                json.dumps(workflow.parameters),
                json.dumps(workflow.shape_key),
                workflow.same_as,
                json.dumps(workflow.unproven),
                datetime.now(tz=UTC).isoformat(),
            ),
        )
        connection.execute("DELETE FROM workflow_steps WHERE workflow_id = ?", (workflow.id,))
        for step in workflow.steps:
            connection.execute(
                "INSERT INTO workflow_steps (workflow_id, ord, says, system, cites, parameters)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    workflow.id,
                    step.order,
                    step.says,
                    step.system,
                    json.dumps(step.cites),
                    json.dumps(step.parameters),
                ),
            )


def known_workflows(store: Store, tenant: str) -> list[Workflow]:
    workflows: list[Workflow] = []
    for row in store.query(
        "SELECT * FROM workflows WHERE tenant = ? ORDER BY created_at", (tenant,)
    ):
        steps = [
            Step(
                order=step["ord"],
                says=step["says"],
                system=step["system"],
                cites=json.loads(step["cites"]),
                parameters=json.loads(step["parameters"]),
            )
            for step in store.query(
                "SELECT * FROM workflow_steps WHERE workflow_id = ? ORDER BY ord",
                (row["id"],),
            )
        ]
        workflows.append(
            Workflow(
                id=row["id"],
                tenant=row["tenant"],
                title=row["title"],
                narrative=row["narrative"],
                systems=json.loads(row["systems"]),
                steps=steps,
                parameters=json.loads(row["parameters"]),
                shape_key=json.loads(row["shape_key"]),
                same_as=row["same_as"],
                unproven=json.loads(row["unproven"]),
                pass_id=row["pass_id"],
            )
        )
    return workflows
