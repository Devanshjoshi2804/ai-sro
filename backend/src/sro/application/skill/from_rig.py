"""A workflow the rig mined, as steps this system can run.

The rig watches a day and proposes workflows; every step of one cites the
gestures it was read from. That citation requirement exists to stop the model
inventing steps -- free generation hallucinated up to 21% of them, citation
forced it under 7.5% -- and it turns out to carry everything a runner needs as
well, because a cited gesture is a real gesture and a real gesture has a real
target.

So the prose a step carries is its description, and its citations are its
mechanism. Measured over the eight workflows mined from 170 hours of real
capture -- 8 workflows, 66 steps, 165 actions:

- all 66 steps produce at least one action
- 62 of 66 resolve to at least one locator; the four that do not cite only
  scrolls, which have no target by design
- 57 of those reach a component query -- the framework's own handle, the
  strongest rung on the ladder
- per action, the strongest rung available is a component query for 118, text
  for 7, css path for 6, role-and-name for 1, and nothing at all for 33 --
  which are the scrolls

The 33 matter to how that last figure is read. An earlier version of this note
said "118 of 132", taking as its denominator only the actions that had ANY
locator, which quietly excluded every action that had none; against all 165 it
is 118, not 89%.

Nothing here reaches for the rig. It consumes the shape stored in the rig's
`gestures.gesture_json` column -- the extension's own wire protocol. **No HTTP
route serves that shape today**: `/v1/gestures` reduces a target to its name
for a human reading a listing, so a caller wiring this to that route gets a
plan with no locators and no error. Serving it belongs with the first consumer
that needs it across the process boundary; until then the two systems share a
shape rather than a dependency, and the source of that shape is the column.
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


def _literal(text: str) -> Template:
    """A recorded string as a template that means only itself.

    `Template` is `string.Template`, so `$` starts a placeholder: a value of
    `A$B` reports `{"B"}` as a parameter it needs, and `render` then either
    raises KeyError or quietly substitutes something the operator never typed.
    Nothing here is a parameter unless a binding says so, and a `$` in a
    recorded value or a css path is a `$` the operator saw. Measured over the
    real corpus: 0 values and 0 css paths contain one, which is the reason this
    is a guard rather than a bug report.
    """
    return Template(raw=text.replace("$", "$$")) if "$" in text else Template(raw=text)


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

    return tuple(ControlLocator(strategy=strategy, query=_literal(raw)) for strategy, raw in rungs)


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


def _order(step: Mapping[str, object]) -> tuple[int, float]:
    """A step's position, from JSON that is not obliged to be sensible.

    Every other field here goes through `_text` or `_mapping`; `order` went
    through neither, and a mix of `1` and `"2"` made `sorted` raise
    TypeError -- while an all-string set sorted lexicographically, putting
    step 10 before step 2 without raising at all, which is worse. Anything
    unusable sorts last rather than at zero: a step whose order nobody can
    read is not a step that ran first.
    """
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


def _control(target: Mapping[str, object] | None) -> str | None:
    """The control a gesture acted on, under the name the rig parameterises by.

    `rig.parameters._by_control` keys a doing by exactly this ladder -- ExtJS
    itemId, then the field's own label, then the accessible name -- so a
    parameter's `name` is one of these strings. Reproduced here to COMPARE
    against, never to mint a name from: a mismatch leaves the value literal,
    which is the safe direction.
    """
    if not target:
        return None
    component = _mapping(target.get("component"))
    return (
        _text(component.get("itemId"))
        or _text(component.get("fieldLabel"))
        or _text(target.get("name"))
    )


def bindings_for(workflow: Mapping[str, object]) -> Mapping[str, frozenset[str]]:
    """Each parameter, against the values that job has been seen to take.

    Keyed by the parameter -- which is to say by the CONTROL, because the rig
    names a parameter after the control it was typed into: an ExtJS itemId, or
    the field's own label. An earlier version keyed this by the value instead,
    to avoid re-deriving that name on this side, and the saving was not worth
    what it cost: two parameters each given `Active` on some doing collapsed to
    one entry, and every gesture carrying that value got whichever name sorted
    first. A value is evidence both sides hold, but a value is not an identity
    -- the control is.
    """
    bound: dict[str, frozenset[str]] = {}
    parameters = workflow.get("parameters")
    for parameter in parameters if isinstance(parameters, list) else ():
        if not isinstance(parameter, Mapping):
            continue
        name = _text(parameter.get("name"))
        seen = parameter.get("seen_values")
        if not name or not isinstance(seen, list):
            continue
        values = frozenset(text for value in seen if (text := _text(value)))
        if values:
            bound[name] = bound.get(name, frozenset()) | values
    return bound


def plan_for_gesture(
    gesture: Mapping[str, object], bindings: Mapping[str, frozenset[str]] | None = None
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
    #
    # Bound only when the value was typed into the control the parameter is
    # NAMED after. Matching on the value alone binds by coincidence: two
    # parameters that were each given "Active" on some doing collide, and the
    # alphabetically-first name wins for both -- and worse, a constant of the
    # job that happens to equal some parameter's value turns into a `$name`
    # the runner will substitute. This is one equality test against a field
    # already in the gesture, not a second implementation of the naming rule.
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
        key=_order,
    )
    bindings = bindings_for(workflow)
    return tuple((step, plans_for_step(step, gestures, bindings)) for step in ordered)
