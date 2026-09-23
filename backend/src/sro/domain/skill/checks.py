from collections.abc import Mapping
from dataclasses import dataclass

from sro.domain.execution.evidence import writes
from sro.domain.observation.gesture import Gesture, passed_through
from sro.domain.observation.identity import K_MIN_SHARED_STEPS
from sro.domain.observation.window import Window
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Step, Workflow, cited_ids, ordered_cites

K_MIN_COVERAGE = 0.5
K_MAX_SKEW = 0.4

_DEFAULT_PORTS = {"http": "80", "https": "443"}


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
    if not workflow.steps:
        return Rejection(workflow.title, "no steps", "a workflow of nothing")

    for step in workflow.steps:
        if not step.cites:
            return Rejection(workflow.title, "uncited step", f"step {step.order}: {step.says}")
        unknown = set(step.cites) - set(evidence)
        if unknown:
            return Rejection(workflow.title, "unknown gesture", ", ".join(sorted(unknown)))
        if not step.says.strip():
            return Rejection(workflow.title, "wordless step", f"step {step.order}")
        for used in step.uses:
            if used >= step.order:
                return Rejection(
                    workflow.title,
                    "step uses a later step",
                    f"step {step.order} uses step {used}",
                )
            if used not in {one.order for one in workflow.steps}:
                return Rejection(
                    workflow.title,
                    "step uses a step that is not there",
                    f"step {step.order} uses step {used}",
                )
        if step.system:
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
    evidenced = {evidence[cite] for cite in cited_ids(workflow)}
    invented = claimed - evidenced
    if invented:
        return Rejection(workflow.title, "system not in evidence", ", ".join(sorted(invented)))

    if len(workflow.steps) < K_MIN_SHARED_STEPS:
        return Rejection(
            workflow.title,
            "too few steps to recognise",
            f"{len(workflow.steps)} step(s); resolve needs {K_MIN_SHARED_STEPS} to match",
        )
    return None


def _gini(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    total = sum(ordered)
    weighted = sum((index + 1) * value for index, value in enumerate(ordered))
    return (2 * weighted) / (n * total) - (n + 1) / n


def coverage(workflows: list[Workflow], window: Window) -> Coverage:
    cited: set[str] = set()
    for workflow in workflows:
        cited |= cited_ids(workflow)

    n = len(window.items)
    deciles = [0.0] * 10
    for index, item in enumerate(window.items):
        if item.gesture_id in cited:
            deciles[index * 10 // n] += 1

    total = sum(deciles)
    if total == 0:
        return Coverage(0.0, 0.0, 0.0)
    mass = [d / total for d in deciles]
    return Coverage(
        coverage=sum(1 for d in deciles if d > 0) / min(10, n),
        skew=sum(mass[:3]) - sum(mass[-3:]),
        gini=_gini(mass),
    )


_WROTE_METHODS = frozenset({"POST", "PUT", "PATCH"})


def _signed_in_here(gesture: Gesture) -> bool:
    target = gesture.action.target
    return bool(gesture.action.secret or (target is not None and target.secret))


def _did_business(gesture: Gesture) -> bool:
    here = origin_of(gesture.system or "")
    return any(
        call.status is not None
        and 200 <= call.status < 300
        and call.method.upper() in _WROTE_METHODS
        and origin_of(call.url) == here
        for call in gesture.requests
    )


def undeliverable(workflow: Workflow, gestures: dict[str, Gesture]) -> list[str]:
    bindable: set[str] = set()
    for step in workflow.steps:
        bindable.update(step.parameters)
        for cite in step.cites:
            gesture = gestures.get(cite)
            target = gesture.action.target if gesture else None
            component = target.component if target else None
            for name in (
                component.item_id if component else None,
                component.field_label if component else None,
                target.name if target else None,
            ):
                if name:
                    bindable.add(name)
    return [
        str(declared["name"])
        for declared in workflow.parameters
        if declared.get("name") and str(declared["name"]) not in bindable
    ]


def _during(workflow: Workflow, gestures: Mapping[str, Gesture]) -> list[Gesture]:
    cited = [gestures[one] for one in ordered_cites(workflow) if one in gestures]
    if not cited:
        return []
    first, last = min(one.at for one in cited), max(one.at for one in cited)
    streams = {one.stream_id for one in cited}
    return [
        gesture
        for gesture in gestures.values()
        if gesture.stream_id in streams and first <= gesture.at <= last
    ]


def signs_in(workflow: Workflow, gestures: Mapping[str, Gesture]) -> bool:
    during = _during(workflow, gestures)
    return (
        any(_signed_in_here(gesture) for gesture in during)
        and not any(_did_business(gesture) for gesture in during)
        and all(
            is_sign_in_step(workflow, step, gestures)
            for step in workflow.steps
            if writes(step, gestures)
        )
    )


def is_sign_in_step(workflow: Workflow, step: Step, gestures: Mapping[str, Gesture]) -> bool:
    cited = [gestures[one] for one in step.cites if one in gestures]
    if not cited or any(_did_business(gesture) for gesture in cited):
        return False
    carries = any(_signed_in_here(gesture) for gesture in cited)
    if carries and not writes(step, gestures):
        return True
    return (carries or _after_the_credential(workflow, step, gestures)) and any(
        passed_through(gesture) for gesture in cited
    )


def _after_the_credential(workflow: Workflow, step: Step, gestures: Mapping[str, Gesture]) -> bool:
    before = [one for one in workflow.steps if one.order < step.order]
    if not before:
        return False
    previous = max(before, key=lambda one: one.order)
    here = {origin_of(gestures[one].system or "") for one in step.cites if one in gestures}
    return any(
        _signed_in_here(gestures[one]) and origin_of(gestures[one].system or "") in here
        for one in previous.cites
        if one in gestures
    )


def work_only(
    workflow: Workflow, gestures: dict[str, Gesture], *, ours: frozenset[str]
) -> Rejection | None:
    cited = [gestures[one] for one in ordered_cites(workflow) if one in gestures]
    order = [gesture.system or "" for gesture in cited]
    last = {system: index for index, system in enumerate(order)}
    bounced = {gesture.system or "" for gesture in cited if passed_through(gesture)}
    transit = {
        system
        for system, index in last.items()
        if system and index < len(order) - 1 and system in bounced
    }

    if signs_in(workflow, gestures) and any(
        passed_through(gesture) for gesture in _during(workflow, gestures)
    ):
        return Rejection(
            workflow.title,
            "not a job",
            "a credential was typed, the browser moved on, and nothing was written",
        )

    kept = [
        system
        for system in workflow.systems
        if origin_of(system) not in ours and system not in transit
    ]
    if workflow.systems and not kept:
        return Rejection(
            workflow.title,
            "not a job",
            "every system it names is this deployment or a hop through one",
        )
    workflow.systems = kept
    return None


K_SITTING_GAP_S = 600.0


def _sittings(times: list[float]) -> list[tuple[float, float]]:
    spans: list[tuple[float, float]] = []
    for at in sorted(times):
        if spans and at - spans[-1][1] <= K_SITTING_GAP_S:
            spans[-1] = (spans[-1][0], at)
        else:
            spans.append((at, at))
    return spans


def one_occurrence(workflow: Workflow, gestures: dict[str, Gesture]) -> None:
    times = [gestures[cited].at for cited in cited_ids(workflow) if cited in gestures]
    if not times:
        return
    spans = _sittings(times)
    if len(spans) < 2:
        return

    def reach(span: tuple[float, float]) -> tuple[int, float]:
        lo, hi = span
        steps = sum(
            1
            for step in workflow.steps
            if any(cited in gestures and lo <= gestures[cited].at <= hi for cited in step.cites)
        )
        return steps, hi

    lo, hi = max(spans, key=reach)
    for step in workflow.steps:
        step.cites = [
            cited for cited in step.cites if cited in gestures and lo <= gestures[cited].at <= hi
        ]
