"""A11 — identity, and it is arithmetic.

Two questions that look like one. Cited gesture ids are per-occurrence, so two
independent doings of the same job cite disjoint sets and their overlap is
always zero -- ids can only tell you whether this is a re-read of a window
already processed. Whether it is the SAME JOB seen on different evidence needs a
key derived from the evidence, compared by containment.

The model's own `same_as` is recorded and decides neither. A model asked to
re-judge its earlier verdict disagrees with itself at roughly 90%, and `same_as`
asks precisely that.
"""

from dataclasses import dataclass

from rig.shape import containment, jaccard
from rig.workflows import Workflow, cited_ids

K_SAME_EVIDENCE = 0.5
K_SAME_JOB = 0.5
# Containment divides by the SMALLER shape, so a two-step workflow is half
# contained by anything sharing a single step -- a lookup both jobs happen to
# begin with would fold two unrelated jobs into one. A ratio alone cannot tell
# "half of two" from "half of twenty", so the overlap must also be real in
# absolute terms.
K_MIN_SHARED_STEPS = 2


@dataclass(frozen=True, slots=True)
class Resolution:
    kind: str  # "new" | "same_occurrence" | "same_job"
    workflow_id: str | None = None
    score: float = 0.0

    # True when MINE is the larger shape -- mine contains theirs. Three states
    # exist and this collapses two of them: "theirs contains mine" and "neither
    # contains the other" are both False here, and they are not the same fact.
    #
    # A bool on purpose, for now. Nothing acts on it: Task 6 flagged the
    # collapse, Task 7 confirmed there was no first consumer, and Task 8
    # confirmed the mining loop does not branch on `same_job` at all -- so the
    # third state would be a distinction drawn for no reader, and a guess at
    # what that reader will want.
    #
    # The caller that needs it is specific and namable: the one that must decide
    # whether to REPLACE a known workflow with this proposal rather than link to
    # it. "Mine contains theirs" is the case for replacing; "theirs contains
    # mine" is the case for discarding mine; "neither" is the case for keeping
    # both. Whoever writes that caller should widen this to those three states
    # rather than reading False as "theirs contains mine".
    contains: bool = False


def _shape_set(workflow: Workflow) -> set[tuple[str, ...]]:
    return {tuple(entry) for entry in workflow.shape_key}


def resolve(proposal: Workflow, known: list[Workflow]) -> Resolution:
    """Which of the known workflows, if any, this proposal already is.

    No guard for an empty shape or an uncited proposal: containment and jaccard
    both return 0.0 for an empty set, no threshold here is at or below zero, and
    a proposal that matches nothing falls out of the bottom as "new" anyway.
    """
    # tenant is the one other field of Workflow that can make two rows
    # unmergeable however alike they look. known_workflows() scopes its query by
    # tenant; resolve() takes whatever list it is handed, and welding one
    # tenant's job onto another's is not a mistake anyone can undo afterwards.
    peers = [other for other in known if other.tenant == proposal.tenant]

    mine = cited_ids(proposal)
    seen: Workflow | None = None
    seen_score = 0.0
    for other in peers:
        score = jaccard(mine, cited_ids(other))
        if score >= K_SAME_EVIDENCE and score > seen_score:
            seen, seen_score = other, score
    if seen is not None:
        # The overlap as measured, not a flat 1.0: three citations of four is
        # the same occurrence and is not identity, and a constant is a number
        # no caller can ever threshold on a second time.
        return Resolution("same_occurrence", seen.id, seen_score)

    shape = _shape_set(proposal)
    best: Workflow | None = None
    best_score = 0.0
    best_contains = False
    for other in peers:
        theirs = _shape_set(other)
        score = containment(shape, theirs)
        # Both bars first, then the best of whatever clears them -- not the best
        # overall and then the bars. A one-step stub is 1.0-contained by
        # anything beginning where it does; ranking before filtering lets it win
        # the comparison, fail the step count, and hide the real match behind it.
        if score >= K_SAME_JOB and len(shape & theirs) >= K_MIN_SHARED_STEPS and score > best_score:
            best, best_score, best_contains = other, score, len(shape) > len(theirs)
    if best is not None:
        return Resolution("same_job", best.id, best_score, contains=best_contains)
    return Resolution("new")
