"""What a proven workflow is, and where it lives."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field


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
    parameters: list[dict[str, object]] = field(default_factory=list)
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


def ordered_cites(workflow: Workflow) -> list[str]:
    """Every gesture the workflow cites, in step order.

    `cited_ids` is a set, and a shape key made in set order is not this job's
    shape -- the key is a SEQUENCE of (system, control, kind), so the order the
    steps run in is half of what it says. Here rather than beside either
    caller: the mining pass writes a shape key and `rekey_workflows` rewrites
    one, and two spellings of "in step order" is two shapes for one job.
    """
    return [cited for step in sorted(workflow.steps, key=lambda s: s.order) for cited in step.cites]
