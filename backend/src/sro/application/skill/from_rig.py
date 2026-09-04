"""A workflow the rig mined, as steps this system can run.

The rig watches a day and proposes workflows; every step of one cites the
gestures it was read from. That citation requirement exists to stop the model
inventing steps -- free generation hallucinated up to 21% of them, citation
forced it under 7.5% -- and it turns out to carry everything a runner needs as
well, because a cited gesture is a real gesture and a real gesture has a real
target.

So the prose a step carries is its description, and its citations are its
mechanism. Measured over the eight workflows mined from 170 hours of real
capture: 62 of 66 steps resolve to at least one locator, and 56 of those to a
component query -- the framework's own handle, the strongest rung on the
ladder. The four that do not cite only scrolls, which have no target by
design.

Nothing here reaches for the rig. It takes the JSON the rig's own routes
already serve, so the two systems share a shape rather than a dependency.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.domain.recording.element import ComponentIdentity, ElementFingerprint
from sro.domain.recording.events import ActionKind
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.plan import UiPlan
from sro.domain.skill.template import Template

# A gesture kind is already an ActionKind by name -- the rig re-declares the
# extension's protocol and this vocabulary comes from the same place. Mapped
# explicitly anyway, so a kind neither side has heard of is a miss rather than
# a crash.
_ACTIONS = {kind.value: kind for kind in ActionKind}

# Which of those a driver cannot perform without knowing where. UiPlan enforces
# the same rule; this is here to answer "why is there no plan for that step"
# without constructing one that will be refused.
_NEEDS_TARGET = {
    ActionKind.CLICK,
    ActionKind.TYPE,
    ActionKind.SELECT,
    ActionKind.PRESS,
    ActionKind.UPLOAD,
    ActionKind.HOVER,
}


def _text(value: object) -> str | None:
    """A JSON value as a string, or None when it is not usable as one.

    Everything arriving here came off `json.loads`, so every field is `object`
    until something looks. A non-string where a name belongs is not a name.
    """
    return value if isinstance(value, str) and value.strip() else None


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def locators_for(target: Mapping[str, object] | None) -> tuple[ControlLocator, ...]:
    """The ladder for one element, strongest strategy first.

    The order is LocatorStrategy's own: a component query is what the
    application's code uses to find the control, and a css path is the last
    resort its docstring calls it. A target with nothing usable yields an empty
    ladder rather than a guessed one -- `UiPlan.replayable` reads that as "the
    demonstration produced nothing worth replaying by", which is a fact about
    the step and not a reason to invent.
    """
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

    return tuple(
        ControlLocator(strategy=strategy, query=Template(raw=raw)) for strategy, raw in rungs
    )


def fingerprint_for(target: Mapping[str, object] | None) -> ElementFingerprint | None:
    """The element as the recorder saw it, or None when it saw nothing usable.

    ElementFingerprint refuses one with no identifying signal, and a scroll
    carries no target at all -- so this returns None rather than letting the
    invariant raise on evidence that is simply not about an element.
    """
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
    """The framework's own handle, when there is a whole one.

    ComponentIdentity refuses a framework or query that is empty, and rightly:
    a component identity with no query identifies nothing. A recorder that
    reached the framework enough to report an itemId but not a query still
    yields a usable one, because `#itemId` is a query in ExtJS's own language --
    which is also the locator this builds from it.
    """
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


def bindings_for(workflow: Mapping[str, object]) -> Mapping[str, str]:
    """Every value the job is known to vary, against the name it varies under.

    Keyed by the VALUE rather than by the control it was typed into, and that is
    a choice. The rig names a parameter after its control -- an ExtJS itemId,
    or the field's label -- and re-deriving that name here would be a second
    implementation of one rule, which is how this codebase came to have three
    word-splitters that disagreed about `SAMLResponse`. A value is evidence
    both sides already hold.

    The cost is that two parameters which have been given the same value once
    would collide. Deliberate: `parameters_across` only reports a control whose
    value CHANGED between doings, so a collision needs two different inputs to
    have shared a value on some doing -- and where that happens, binding either
    name produces the same run, because the run supplies the value.
    """
    bound: dict[str, str] = {}
    parameters = workflow.get("parameters")
    for parameter in parameters if isinstance(parameters, list) else ():
        if not isinstance(parameter, Mapping):
            continue
        name = _text(parameter.get("name"))
        seen = parameter.get("seen_values")
        if not name or not isinstance(seen, list):
            continue
        for value in seen:
            text = _text(value)
            if text:
                bound.setdefault(text, name)
    return bound


def plan_for_gesture(
    gesture: Mapping[str, object], bindings: Mapping[str, str] | None = None
) -> UiPlan | None:
    """One recorded gesture as one step a driver could perform.

    None where the gesture is not a thing to replay: an unknown kind, or an
    action that needs a target and has no locator to find one by. The caller is
    expected to keep the step and record that it cannot be run, because a step
    silently missing from a plan is a job that will not do what it says.
    """
    action = _ACTIONS.get(_text(gesture.get("kind")) or "")
    if action is None:
        return None

    target = _mapping(gesture.get("target")) or None
    locators = locators_for(target)
    if action in _NEEDS_TARGET and not locators:
        return None

    # A credential never reaches here: wire.Gesture drops the value at the
    # parse boundary and trim/redaction re-check it. A value that survived to
    # this point is the operator's own data, and it becomes a template because
    # a run may be asked to type a different one.
    value = _text(gesture.get("value"))
    # A value the job is known to vary becomes the name it varies under, so a
    # run can be asked for a different one. A value nobody has seen vary stays
    # literal -- it is part of the job until evidence says otherwise, and
    # guessing which literals are really inputs is the thing two doings exist
    # to avoid.
    if value and bindings:
        name = bindings.get(value)
        if name:
            value = f"${name}"
    return UiPlan(
        action=action,
        target=fingerprint_for(target),
        value=Template(raw=value) if value else None,
        locators=locators,
    )


def plans_for_step(
    step: Mapping[str, object],
    gestures: Mapping[str, Mapping[str, object]],
    bindings: Mapping[str, str] | None = None,
) -> tuple[UiPlan, ...]:
    """Every runnable action a step's citations name, in the order cited.

    A step is prose plus citations. The prose says what it was for; these are
    what it did. A citation naming a gesture nobody has is skipped rather than
    guessed at -- the rig's own `validate` refuses a workflow citing evidence
    that does not exist, so reaching this with one means the store moved.
    """
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
    """Each step beside what it would run, steps that run nothing included.

    The empty tuple is the point: a step citing only scrolls produces no plan,
    and a caller that dropped it would offer a job missing a step it was
    described as having.
    """
    steps = workflow.get("steps")
    ordered: Sequence[Mapping[str, object]] = sorted(
        (s for s in (steps if isinstance(steps, list) else ()) if isinstance(s, Mapping)),
        key=lambda step: step.get("order", 0),  # type: ignore[arg-type,return-value]
    )
    bindings = bindings_for(workflow)
    return tuple((step, plans_for_step(step, gestures, bindings)) for step in ordered)
