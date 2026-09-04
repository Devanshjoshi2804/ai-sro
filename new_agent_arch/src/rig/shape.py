"""A5 — the shape key: what makes two doings the same job.

Cited gesture ids are per-occurrence, so two independent doings of one job cite
disjoint sets and overlap on them is always zero. That question -- "is this a
re-read of evidence I have already processed" -- is answered by ids. This is the
other question: "is this the same job as one I saw on different evidence", and
it needs a key derived from the evidence rather than the evidence itself.

Never cssPath or xpath: both encode document position, both change when the page
is restyled, and a key built on them is the brittleness this replaces.
"""

from collections.abc import Set as AbstractSet

from rig.records import Gesture

ShapeKey = tuple[tuple[str, str, str], ...]


def target_identity(gesture: Gesture) -> str:
    """What to call the control this gesture touched, stably across occurrences."""
    target = gesture.gesture.target
    if target is None:
        # A scroll has no target -- you scroll a page, not an element.
        return f"anon|{gesture.gesture.kind}"

    component = target.component
    if component is not None:
        if component.itemId:
            return component.itemId
        if component.query:
            return component.query
    if target.role and target.name:
        return f"{target.role}|{target.name}"
    if target.name:
        return f"name|{target.name}"
    if target.testId:
        return f"test|{target.testId}"
    if target.text:
        return f"text|{target.text}"
    return f"anon|{gesture.gesture.kind}"


def shape_key(gestures: list[Gesture]) -> ShapeKey:
    """The job's shape: which control, on which system, touched how -- in order."""
    return tuple(
        (gesture.system or "", target_identity(gesture), gesture.gesture.kind)
        for gesture in gestures
    )


def containment(a: AbstractSet[object], b: AbstractSet[object]) -> float:
    """|a ∩ b| / min(|a|, |b|).

    Containment rather than Jaccard, because a three-step "create supplier" sits
    INSIDE a twelve-step "create supplier, add item, set status in SAP". Jaccard
    drowns the small set in the union and calls them different jobs; containment
    says the smaller is part of the larger, which is true and is the variant
    relation worth surfacing.
    """
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def jaccard(a: AbstractSet[object], b: AbstractSet[object]) -> float:
    """|a ∩ b| / |a ∪ b|. For the occurrence question, where the two sets are
    the same size by construction."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)
