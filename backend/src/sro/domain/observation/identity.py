from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Workflow, cited_ids

ShapeKey = tuple[tuple[str, str, str], ...]


K_TEXT_IDENTITY_MAX = 40


def _names_a_control(text: str) -> bool:
    return "\n" not in text and len(text) <= K_TEXT_IDENTITY_MAX


def target_identity(gesture: Gesture) -> str:
    target = gesture.action.target
    if target is None:
        return f"anon|{gesture.action.kind}"

    component = target.component
    if component is not None:
        if component.item_id:
            return component.item_id
        if component.query:
            return component.query
    if target.role and target.name and _names_a_control(target.name):
        return f"{target.role}|{target.name}"
    if target.name and _names_a_control(target.name):
        return f"name|{target.name}"
    if target.test_id:
        return f"test|{target.test_id}"
    if target.text and _names_a_control(target.text):
        return f"text|{target.text}"
    return f"anon|{gesture.action.kind}"


def screen_of(gesture: Gesture) -> str:
    said = gesture.page_url or gesture.url or gesture.system or ""
    if not said:
        return ""
    parsed = urlsplit(said)
    where = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/").lower()
    route = "/".join(part for part in parsed.fragment.split("/") if part and "." in part).lower()
    return f"{where}#{route}" if route else where


def shape_key(gestures: list[Gesture]) -> ShapeKey:
    return tuple(
        (screen_of(gesture), target_identity(gesture), gesture.action.kind) for gesture in gestures
    )


K_SAME_NAME = 0.5

NOT_A_NAME = frozenset({"a", "an", "the", "to", "for", "of", "in", "on", "and"})


def _as_words(title: str) -> frozenset[str]:
    return frozenset(
        word
        for word in "".join(
            char if char.isalnum() or char.isspace() else " " for char in title.lower()
        ).split()
        if word not in NOT_A_NAME
    )


def named_alike(mine: str, theirs: str) -> bool:
    ours, others = _as_words(mine), _as_words(theirs)
    if not ours or not others:
        return True
    return len(ours & others) / len(ours | others) >= K_SAME_NAME


def containment(a: AbstractSet[object], b: AbstractSet[object]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def jaccard(a: AbstractSet[object], b: AbstractSet[object]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


K_SAME_EVIDENCE = 0.5
K_SAME_JOB = 0.5
K_MIN_SHARED_STEPS = 2


@dataclass(frozen=True, slots=True)
class Resolution:
    kind: str
    workflow_id: str | None = None
    score: float = 0.0

    contains: bool = False


def _shape_set(workflow: Workflow) -> set[tuple[str, ...]]:
    return {tuple(entry) for entry in workflow.shape_key}


ANON = "anon|"


def _shared(mine: set[tuple[str, ...]], theirs: set[tuple[str, ...]]) -> int:
    left = set(mine)
    right = set(theirs)
    shared = left & right
    left -= shared
    right -= shared
    named = sorted(one for one in right if not one[1].startswith(ANON))
    for one in sorted(one for one in left if one[1].startswith(ANON)):
        if any(other[0] == one[0] and other[2] == one[2] for other in named):
            shared.add(one)
    return len(shared)


def resolve(proposal: Workflow, known: list[Workflow]) -> Resolution:
    peers = [other for other in known if other.tenant == proposal.tenant]

    mine = cited_ids(proposal)
    seen: Workflow | None = None
    seen_score = 0.0
    for other in peers:
        score = jaccard(mine, cited_ids(other))
        if score >= K_SAME_EVIDENCE and score > seen_score:
            seen, seen_score = other, score
    if seen is not None:
        return Resolution("same_occurrence", seen.id, seen_score)

    shape = _shape_set(proposal)
    best: Workflow | None = None
    best_score = 0.0
    best_contains = False
    for other in peers:
        theirs = _shape_set(other)
        matched = _shared(shape, theirs)
        score = matched / min(len(shape), len(theirs)) if shape and theirs else 0.0
        whole = matched >= K_MIN_SHARED_STEPS or matched == len(shape)
        if (
            score >= K_SAME_JOB
            and whole
            and score > best_score
            and named_alike(proposal.title, other.title)
        ):
            best, best_score, best_contains = other, score, len(shape) > len(theirs)
    if best is not None:
        return Resolution("same_job", best.id, best_score, contains=best_contains)
    return Resolution("new")
