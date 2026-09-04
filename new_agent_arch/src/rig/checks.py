"""A9, A10 — the only code here that overrules a model.

None of it reads a URL, a body or a call shape. It asks whether a workflow has
any steps at all, whether every step cites something, whether everything cited
exists, whether every step says something a person could act on, and whether the
workflow claims only systems its own evidence touches. Then it measures where in
the window the citations fell, because long-context citation bias is real, is
model-specific, and is invisible without counting.
"""

from dataclasses import dataclass

from rig.window import Window
from rig.workflows import Workflow, cited_ids

K_MIN_COVERAGE = 0.5
K_MAX_SKEW = 0.4


@dataclass(frozen=True, slots=True)
class Rejection:
    workflow_title: str
    reason: str
    detail: str


@dataclass(frozen=True, slots=True)
class Coverage:
    coverage: float
    skew: float
    gini: float


def validate(workflow: Workflow, known_ids: set[str]) -> Rejection | None:
    """None when the workflow may be kept, a Rejection when it may not."""
    # umbrella._as_workflow drops junk steps one at a time, so a workflow whose
    # steps were ALL junk arrives here with steps=[] and no citations at all --
    # nothing uncited for the loop below to catch. This is that rejection.
    if not workflow.steps:
        return Rejection(workflow.title, "no steps", "a workflow of nothing")

    for step in workflow.steps:
        if not step.cites:
            return Rejection(workflow.title, "uncited step", f"step {step.order}: {step.says}")
        unknown = set(step.cites) - known_ids
        if unknown:
            return Rejection(workflow.title, "unknown gesture", ", ".join(sorted(unknown)))
        # cites' sibling. _as_workflow falls back to says="" for a step the
        # model left unworded, and a step that says nothing is not a step
        # however well it is cited -- it reaches an operator as a blank line.
        if not step.says.strip():
            return Rejection(workflow.title, "wordless step", f"step {step.order}")

    claimed = {s for s in workflow.systems if s}
    # No `if step.system` filter: `claimed` is already truthy-only, so a None
    # here can never match anything it is subtracted from. Filtering both sides
    # is one guard pretending to be two -- deleting it changed no test.
    evidenced = {step.system for step in workflow.steps}
    invented = claimed - evidenced
    if invented:
        return Rejection(workflow.title, "system not in evidence", ", ".join(sorted(invented)))
    return None


def _gini(values: list[float]) -> float:
    """How unequally the citations are spread. Only ever called with a full
    decile list that sums to 1, so it needs no empty case."""
    ordered = sorted(values)
    n = len(ordered)
    total = sum(ordered)
    weighted = sum((index + 1) * value for index, value in enumerate(ordered))
    return (2 * weighted) / (n * total) - (n + 1) / n


def coverage(workflows: list[Workflow], window: Window) -> Coverage:
    """Which parts of the window were cited at all, and where they clustered."""
    cited: set[str] = set()
    for workflow in workflows:
        cited |= cited_ids(workflow)

    n = len(window.items)
    deciles = [0.0] * 10
    for index, item in enumerate(window.items):
        if item.gesture_id in cited:
            deciles[index * 10 // n] += 1

    # An empty window skips the loop and lands here, so this is also the
    # no-items case: one return for "no citation fell anywhere in it".
    total = sum(deciles)
    if total == 0:
        return Coverage(0.0, 0.0, 0.0)
    mass = [d / total for d in deciles]
    return Coverage(
        # Over min(10, n) rather than a flat ten: a window of four gestures has
        # four parts and can only ever land in four deciles, so dividing by ten
        # reported a FULLY cited short window at 0.4 -- under K_MIN_COVERAGE.
        coverage=sum(1 for d in deciles if d > 0) / min(10, n),
        skew=sum(mass[:3]) - sum(mass[-3:]),
        gini=_gini(mass),
    )
