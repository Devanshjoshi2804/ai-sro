"""A13: what a step knows before any model is asked.

A step cites gestures; those gestures carry recorder.js fingerprints; so the
locator list the protocol wants is built from the cited evidence with no model
involved, in the protocol's own priority order. `origin` is per step, from that
step's own evidence -- in a job spanning two systems the Blue Yonder steps carry
Blue Yonder's origin and the SAP step carries SAP's. A documented
cross-application agent failure is losing window focus during a hand-off, so
data meant for the second application is typed into the first; this is what
stops it.
"""

from collections.abc import Mapping
from typing import Any

from rig.correlate import system_of
from rig.records import Gesture
from rig.wire import Request
from rig.workflows import Step, Workflow

_UNTARGETED = frozenset({"scroll"})


def _locator(strategy: str, query: str) -> dict[str, Any]:
    return {"strategy": strategy, "query": query, "within": None, "visible_only": True}


def locators_for(gesture: Gesture) -> list[dict[str, Any]]:
    """The ladder, strongest first: the framework's own handle, then role and
    name, then visible text, then the test id, then the css path the protocol
    calls a last resort. A gesture with no target -- a scroll -- has no ladder."""
    target = gesture.gesture.target
    if target is None:
        return []
    ladder: list[dict[str, Any]] = []
    component = target.component
    if component is not None:
        query = component.query or (f"#{component.itemId}" if component.itemId else None)
        if query:
            ladder.append(_locator("component", query))
    if target.role and target.name:
        ladder.append(_locator("role_and_name", f"{target.role}|{target.name}"))
    if target.text:
        ladder.append(_locator("text", target.text))
    if target.testId:
        ladder.append(_locator("test_id", target.testId))
    if target.cssPath:
        ladder.append(_locator("css_path", target.cssPath))
    return ladder


def origin_of(gesture: Gesture) -> str | None:
    """Scheme and host of the first call that names a system, else of the page."""
    for request in gesture.requests:
        system = system_of(request.url)
        if system:
            return system
    return gesture.system or system_of(gesture.url)


def primary_gesture(step: Step, by_id: Mapping[str, Gesture]) -> Gesture | None:
    """The first cited gesture that exists and can be acted on."""
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is not None and gesture.gesture.kind not in _UNTARGETED:
            return gesture
    return None


def recorded_call(step: Step, by_id: Mapping[str, Gesture]) -> Request | None:
    """The call this step's evidence made: the first mutation, else the first
    call at all. What `http.send` would replay, and what `verify` reads an
    expected status from."""
    reads: list[Request] = []
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for request in gesture.requests:
            if request.method.upper() not in ("GET", "HEAD", "OPTIONS"):
                return request
            reads.append(request)
    return reads[0] if reads else None


def writes(step: Step, by_id: Mapping[str, Gesture]) -> bool:
    """Whether performing this step changes something. A dry run withholds it."""
    call = recorded_call(step, by_id)
    return call is not None and call.method.upper() not in ("GET", "HEAD", "OPTIONS")


def allowlist(workflow: Workflow, by_id: Mapping[str, Gesture]) -> set[str]:
    """Every system the workflow's own cited evidence names. A planned command
    to any other origin is refused before it leaves the process."""
    named: set[str] = set()
    for step in workflow.steps:
        for cited in step.cites:
            gesture = by_id.get(cited)
            if gesture is None:
                continue
            for candidate in (gesture.system, system_of(gesture.url)):
                if candidate:
                    named.add(candidate)
            for request in gesture.requests:
                system = system_of(request.url)
                if system:
                    named.add(system)
    return named
