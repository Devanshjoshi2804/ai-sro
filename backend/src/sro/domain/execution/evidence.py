from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass

from sro.domain.observation.gesture import Call, Gesture
from sro.domain.recording.background import is_background_traffic
from sro.domain.shared.hosts import same_screen, screen_of, system_of
from sro.domain.skill.workflow import Step, Workflow, field_key

_UNTARGETED = frozenset({"scroll"})

K_CAUSED_S = 0.5

CREATED = 201

READ_METHODS = ("GET", "HEAD", "OPTIONS")


@dataclass(frozen=True, slots=True)
class Locator:
    strategy: str
    query: str
    within: str | None = None
    visible_only: bool = True

    def as_payload(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "query": self.query,
            "within": self.within,
            "visible_only": self.visible_only,
        }


def _locator(strategy: str, query: str) -> Locator:
    return Locator(strategy, query)


def locators_for(gesture: Gesture) -> list[Locator]:
    target = gesture.action.target
    if target is None:
        return []
    ladder: list[Locator] = []
    component = target.component
    if component is not None:
        query = component.query or (f"#{component.item_id}" if component.item_id else None)
        if query:
            leaf = _stable_leaf(target.css_path)
            if leaf and str(component.xtype or "").lower().endswith("view"):
                ladder.append(Locator("css_path", leaf, within=query))
            ladder.append(_locator("component", query))
    if target.role and target.name:
        ladder.append(_locator("role_and_name", f"{target.role}|{target.name}"))
    if target.text:
        ladder.append(_locator("text", target.text))
    if target.test_id:
        ladder.append(_locator("test_id", target.test_id))
    if target.css_path:
        ladder.append(_locator("css_path", target.css_path))
    return ladder


def _stable_leaf(css_path: str | None) -> str:
    if not css_path:
        return ""
    last = css_path.split(">")[-1].split()[-1] if css_path.strip() else ""
    kept = re.sub(r"#[^.#:\[]+|:nth-[a-z-]+\([^)]*\)", "", last)
    return kept if "." in kept else ""


def origin_of(gesture: Gesture) -> str | None:
    page = gesture.system or system_of(gesture.url)
    if page:
        return page
    named = [system_of(r.url) for r in gesture.requests]
    completed = [
        s
        for r, s in zip(gesture.requests, named, strict=True)
        if s and r.status is not None and not r.failure_reason
    ]
    if completed:
        return completed[0]
    return next((s for s in named if s), None)


PUTS_A_VALUE = frozenset({"type", "select", "upload"})


def primary_gesture(
    step: Step, by_id: Mapping[str, Gesture], holds: Collection[str] = frozenset()
) -> Gesture | None:
    cited = [
        gesture
        for one in step.cites
        if (gesture := by_id.get(one)) is not None and gesture.action.kind not in _UNTARGETED
    ]
    put = [one for one in cited if one.action.kind in PUTS_A_VALUE]
    held = next((one for one in put if control_names(one) & set(holds)), None)
    if held is not None:
        return held
    if step.parameters and put:
        return put[0]
    return cited[0] if cited else None


def control_names(gesture: Gesture) -> set[str]:
    target = gesture.action.target
    component = target.component if target else None
    return {
        name
        for name in (
            component.item_id if component else None,
            component.field_label if component else None,
            target.name if target else None,
        )
        if name
    }


def unperformable(
    workflow: Workflow, by_id: Mapping[str, Gesture], *, from_step: int
) -> Step | None:
    for step in sorted(workflow.steps, key=lambda step: step.order):
        if (
            step.order >= from_step
            and primary_gesture(step, by_id) is None
            and not field_key(workflow, step)
        ):
            return step
    return None


def _caused_by(gesture: Gesture, call: Call) -> bool:
    if call.started_at is None or gesture.at is None:
        return True
    return abs(call.started_at - gesture.at) <= K_CAUSED_S


def recorded_call(step: Step, by_id: Mapping[str, Gesture]) -> Call | None:
    reads: list[Call] = []
    mutations: list[Call] = []
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        origin = origin_of(gesture)
        for request in gesture.requests:
            if origin is not None and system_of(request.url) != origin:
                continue
            if not _caused_by(gesture, request):
                continue
            if is_background_traffic(request.url):
                continue
            if request.method.upper() not in READ_METHODS:
                mutations.append(request)
            else:
                reads.append(request)
    for request in mutations:
        if request.status == CREATED and not request.failure_reason:
            return request
    if mutations:
        return mutations[0]
    return reads[0] if reads else None


def writes(step: Step, by_id: Mapping[str, Gesture]) -> bool:
    call = recorded_call(step, by_id)
    return call is not None and call.method.upper() not in READ_METHODS


def route_for(step: Step, after: Step | None, by_id: Mapping[str, Gesture]) -> str | None:
    if after is None or writes(step, by_id):
        return None
    cited = [by_id[one] for one in step.cites if one in by_id]
    if not cited or any(one.action.kind != "click" or one.action.value for one in cited):
        return None
    here = _agreed(step, by_id)
    there = _agreed(after, by_id)
    if there is None or not there.startswith(("http://", "https://")):
        return None
    return None if same_screen(here, there) else there


def _agreed(step: Step, by_id: Mapping[str, Gesture]) -> str | None:
    seen = [by_id[one] for one in step.cites if one in by_id]
    return screen_of([one.page_url or one.url for one in seen]) if seen else None


def stood_on(workflow: Workflow, by_id: Mapping[str, Gesture]) -> set[str]:
    named: set[str] = set()
    for step in workflow.steps:
        for cited in step.cites:
            gesture = by_id.get(cited)
            if gesture is None:
                continue
            for candidate in (gesture.system, system_of(gesture.url)):
                if candidate:
                    named.add(candidate)
    return named


def allowlist(workflow: Workflow, by_id: Mapping[str, Gesture]) -> set[str]:
    named = stood_on(workflow, by_id)
    for step in workflow.steps:
        for cited in step.cites:
            gesture = by_id.get(cited)
            if gesture is None:
                continue
            for request in gesture.requests:
                system = system_of(request.url)
                if system:
                    named.add(system)
    return named
