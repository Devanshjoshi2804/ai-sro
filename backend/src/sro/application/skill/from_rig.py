from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from sro.domain.recording.element import ComponentIdentity, ElementFingerprint
from sro.domain.recording.events import ActionKind
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.plan import UiPlan
from sro.domain.skill.template import Template

_ACTIONS = {kind.value: kind for kind in ActionKind}

_NEEDS_TARGET = {
    ActionKind.CLICK,
    ActionKind.TYPE,
    ActionKind.SELECT,
    ActionKind.PRESS,
    ActionKind.UPLOAD,
    ActionKind.HOVER,
}


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _literal(text: str) -> Template:
    return Template(raw=text.replace("$", "$$")) if "$" in text else Template(raw=text)


def locators_for(target: Mapping[str, object] | None) -> tuple[ControlLocator, ...]:
    if not target:
        return ()
    component = _mapping(target.get("component"))
    rungs: list[tuple[LocatorStrategy, str]] = []

    item = _text(component.get("itemId"))
    query = _text(component.get("query")) or (f"#{item}" if item else None)
    role, name = _text(target.get("role")), _text(target.get("name"))
    for strategy, raw in (
        (LocatorStrategy.COMPONENT, query),
        (LocatorStrategy.TEST_ID, _text(target.get("testId"))),
        (LocatorStrategy.ROLE_AND_NAME, f"{role}|{name}" if role and name else None),
        (LocatorStrategy.TEXT, _text(target.get("text"))),
        (LocatorStrategy.CSS_PATH, _text(target.get("cssPath"))),
    ):
        if raw:
            rungs.append((strategy, raw))

    return tuple(ControlLocator(strategy=strategy, query=_literal(raw)) for strategy, raw in rungs)


def fingerprint_for(target: Mapping[str, object] | None) -> ElementFingerprint | None:
    if not target:
        return None
    if not any(_text(target.get(key)) for key in ("role", "name", "text", "testId", "cssPath")):
        return None
    component = _mapping(target.get("component"))
    return ElementFingerprint(
        role=_text(target.get("role")),
        accessible_name=_text(target.get("name")),
        text=_text(target.get("text")),
        test_id=_text(target.get("testId")),
        css_path=_text(target.get("cssPath")),
        xpath=_text(target.get("xpath")),
        tag=_text(target.get("tag")),
        component=_component(component),
    )


def _component(component: Mapping[str, object]) -> ComponentIdentity | None:
    if not component:
        return None
    item = _text(component.get("itemId"))
    query = _text(component.get("query")) or (f"#{item}" if item else None)
    xtype = _text(component.get("xtype"))
    framework = _text(component.get("framework")) or ("extjs" if xtype else None)
    if not query or not framework:
        return None
    return ComponentIdentity(
        framework=framework,
        query=query,
        xtype=xtype,
        item_id=item,
        name=_text(component.get("name")),
        field_label=_text(component.get("fieldLabel")),
        text=_text(component.get("text")),
    )


def _order(step: Mapping[str, object]) -> tuple[int, float]:
    raw = step.get("order")
    if isinstance(raw, bool):
        return (1, 0.0)
    if isinstance(raw, int | float):
        return (0, float(raw))
    if isinstance(raw, str):
        try:
            return (0, float(raw.strip()))
        except ValueError:
            return (1, 0.0)
    return (1, 0.0)


_NOT_A_NAME = re.compile(r"[^A-Za-z0-9_]")


def parameter_name(raw: str) -> str:
    cleaned = _NOT_A_NAME.sub("_", raw).strip("_")
    if not cleaned:
        return "parameter"
    return f"p_{cleaned}" if cleaned[0].isdigit() else cleaned


def _control(target: Mapping[str, object] | None) -> str | None:
    if not target:
        return None
    component = _mapping(target.get("component"))
    raw = (
        _text(component.get("itemId"))
        or _text(component.get("fieldLabel"))
        or _text(target.get("name"))
    )
    return parameter_name(raw) if raw else None


def declared_parameters(
    workflow: Mapping[str, object],
) -> dict[str, tuple[str, tuple[str, ...]]]:
    parameters = workflow.get("parameters")
    found: dict[str, tuple[str, tuple[str, ...]] | None] = {}
    for entry in parameters if isinstance(parameters, list) else ():
        if not isinstance(entry, Mapping):
            continue
        raw = _text(entry.get("name"))
        if not raw:
            continue
        name = parameter_name(raw)
        if name in found:
            found[name] = None
            continue
        seen = entry.get("seen_values")
        values = tuple(
            text for value in (seen if isinstance(seen, list) else ()) if (text := _text(value))
        )
        found[name] = (raw, values)
    return {name: entry for name, entry in found.items() if entry is not None}


def bindings_for(workflow: Mapping[str, object]) -> Mapping[str, frozenset[str]]:
    return {
        name: frozenset(values)
        for name, (_, values) in declared_parameters(workflow).items()
        if values
    }


def plan_for_gesture(
    gesture: Mapping[str, object], bindings: Mapping[str, frozenset[str]] | None = None
) -> UiPlan | None:
    action = _ACTIONS.get(_text(gesture.get("kind")) or "")
    if action is None:
        return None

    target = _mapping(gesture.get("target")) or None
    locators = locators_for(target)
    if action in _NEEDS_TARGET and not locators:
        return None

    value = _text(gesture.get("value"))
    template = _literal(value) if value else None
    if value and bindings:
        name = _control(target)
        if name and value in bindings.get(name, ()):
            template = Template(raw=f"${name}")
    return UiPlan(
        action=action,
        target=fingerprint_for(target),
        value=template,
        locators=locators,
    )


def plans_for_step(
    step: Mapping[str, object],
    gestures: Mapping[str, Mapping[str, object]],
    bindings: Mapping[str, frozenset[str]] | None = None,
) -> tuple[UiPlan, ...]:
    plans = []
    cites = step.get("cites")
    for cited in cites if isinstance(cites, list) else ():
        gesture = gestures.get(_text(cited) or "")
        if gesture is None:
            continue
        plan = plan_for_gesture(gesture, bindings)
        if plan is not None:
            plans.append(plan)
    return tuple(plans)


def plans_for_workflow(
    workflow: Mapping[str, object], gestures: Mapping[str, Mapping[str, object]]
) -> tuple[tuple[Mapping[str, object], tuple[UiPlan, ...]], ...]:
    steps = workflow.get("steps")
    ordered: Sequence[Mapping[str, object]] = sorted(
        (s for s in (steps if isinstance(steps, list) else ()) if isinstance(s, Mapping)),
        key=_order,
    )
    bindings = bindings_for(workflow)
    return tuple((step, plans_for_step(step, gestures, bindings)) for step in ordered)
