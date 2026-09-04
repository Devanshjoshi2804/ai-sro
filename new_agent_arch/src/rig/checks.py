"""A9, A10 — the only code here that overrules a model.

None of it reads a URL, a body or a call shape. It asks whether a workflow has
any steps at all, whether every step cites something, whether everything cited
exists, whether every step says something a person could act on, and whether
every system named -- by a step or by the workflow -- is one the cited evidence
actually happened on. Then it measures where in the window the citations fell,
because long-context citation bias is real, is model-specific, and is invisible
without counting.
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


def validate(workflow: Workflow, evidence: dict[str, str]) -> Rejection | None:
    """None when the workflow may be kept, a Rejection when it may not.

    `evidence` maps a gesture id in the window to the system it happened on --
    `Gesture.system`, which is scheme and host. A missing or empty value means
    the system could not be established for that gesture.

    A mapping rather than a set of ids because the system checks below are the
    reason this module exists. Taking `step.system` as the evidence for
    `step.system` compared the model against itself: it caught an answer that
    contradicted its own step list and could not catch one that was internally
    tidy and wholly invented -- which, in an architecture built to find jobs
    spanning two systems, is the one lie it must not accept.
    """
    # umbrella._as_workflow drops junk steps one at a time, so a workflow whose
    # steps were ALL junk arrives here with steps=[] and no citations at all --
    # nothing uncited for the loop below to catch. This is that rejection.
    if not workflow.steps:
        return Rejection(workflow.title, "no steps", "a workflow of nothing")

    for step in workflow.steps:
        if not step.cites:
            return Rejection(workflow.title, "uncited step", f"step {step.order}: {step.says}")
        unknown = set(step.cites) - set(evidence)
        if unknown:
            return Rejection(workflow.title, "unknown gesture", ", ".join(sorted(unknown)))
        # cites' sibling. _as_workflow falls back to says="" for a step the
        # model left unworded, and a step that says nothing is not a step
        # however well it is cited -- it reaches an operator as a blank line.
        if not step.says.strip():
            return Rejection(workflow.title, "wordless step", f"step {step.order}")
        # A step naming no system is not checked for one: the umbrella
        # substitutes None for a junk value, so an absent system is a silence
        # rather than a claim.
        if step.system:
            # An unknown system confirms nothing -- the rule shared_values and
            # correlate._owner already apply. So a step whose every citation is
            # unattributed is refused rather than waved through, and it is
            # refused under its own reason: "you named a system none of your
            # evidence touched" and "your evidence has no known system" are
            # different faults and diagnose differently.
            touched = {evidence[cite] for cite in step.cites if evidence[cite]}
            if not touched:
                return Rejection(
                    workflow.title,
                    "unattributed evidence",
                    f"step {step.order} claims {step.system}; no cited gesture has a system",
                )
            if step.system not in touched:
                return Rejection(
                    workflow.title,
                    "step system not in evidence",
                    f"step {step.order}: {step.system}",
                )

    claimed = {s for s in workflow.systems if s}
    # Every cite is in `evidence` by now, so this is the whole of what the
    # workflow actually stood on. `systems` is its own model output rather than
    # a summary of the steps, so it can name a system no step ever did.
    #
    # No `if evidence[cite]` filter, unlike the step check above, which needs
    # one to tell "no known system" from "the wrong system". Here `claimed` is
    # already truthy-only, so an unknown system arriving as "" can never match
    # anything it is subtracted from. Filtering both sides is one guard
    # pretending to be two -- deleting it changed no test.
    evidenced = {evidence[cite] for cite in cited_ids(workflow)}
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
