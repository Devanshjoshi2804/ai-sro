"""The model call that turns one step of a demonstrated job into one command.

Ported from `plan_step` and `plan_by_sight` in
`new_agent_arch/src/rig/planner.py`. The pure half -- the schemas, the words,
the value rule and the replayability rule -- is
`sro.domain.execution.planning`, and the locator ladder is
`sro.domain.execution.evidence`; this is the half that asks a model and
assembles the payload.

The model answers a small shape -- which kind of command, which action, which
value, which url -- and this assembles the rest. The locators never come from
the model: they are built from the cited evidence, and the extension tries them
in order. What the model decides is only what to do with them, and it is told
to prefer driving the interface over replaying a call.

That preference was measured, not assumed. 544 of the real store's request
headers are CSRF tokens, every one redacted at the rig's boundary. An
`http.send` replaying the recorded call would send the marker as its token and
be refused; clicking Save lets the page mint its own. So `http.send` is for a
step whose evidence carries a call and no usable target -- and a header whose
stored value is the redaction marker is never sent under any plan.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import get_args

from sro.application.capture.rig_wire import headers_without_markers
from sro.application.ports.model import Asker
from sro.domain.execution.evidence import locators_for, primary_gesture, recorded_call
from sro.domain.execution.planning import (
    KINDS,
    PLAN_INSTRUCTIONS,
    PLAN_SCHEMA,
    SIGHT_ACTIONS,
    SIGHT_INSTRUCTIONS,
    SIGHT_SCHEMA,
    Look,
    Planned,
    unreplayable,
    value_for,
)
from sro.domain.observation.gesture import Gesture, Kind
from sro.domain.observation.trim import trim
from sro.domain.shared.prices import Answer, Effort
from sro.domain.skill.workflow import Step

ACTIONS: frozenset[str] = frozenset(get_args(Kind))
"""What a `ui.perform` may ask for: the gesture kinds the recorder records, and
no others. One list, because a plan the extension is asked to perform is a
gesture the recorder could have seen -- `PLAN_SCHEMA` offers the model exactly
these, and `test_the_actions_offered_are_the_actions_accepted` fails if the two
ever part."""

VALUED = ("type", "select", "upload", "press")
"""The actions that carry a value. A click types nothing."""


def _primary(step: Step, cited: list[Gesture]) -> Gesture | None:
    """The gesture this step is planned from.

    `primary_gesture` prefers one the extension can act on and so skips a
    scroll -- but a step citing nothing else is not a step to give up on, and
    falls back to the first cited gesture rather than planning nothing.
    """
    found = primary_gesture(step, {gesture.id: gesture for gesture in cited})
    return found or (cited[0] if cited else None)


async def plan_step(
    *,
    step: Step,
    cited: list[Gesture],
    values: Mapping[str, str],
    look: Look,
    origin: str | None,
    starts_on: str | None,
    allow_focus: bool,
    asker: Asker,
    model: str,
    effort: Effort | None = None,
    failure: str | None = None,
    failed_look: Look | None = None,
) -> Planned:
    primary = _primary(step, cited)
    evidence = json.dumps(
        {
            "step": {"order": step.order, "says": step.says, "parameters": step.parameters},
            "evidence": [trim(gesture) for gesture in cited],
            "values": dict(values),
            "browser": {"url": look.url, "screen_text": look.digest},
            # The real page, not `trim()`'s starred path shape: a step deep in a
            # job was demonstrated on a specific screen, and the planner can only
            # say "navigate there first" if it is told where there is.
            "step_page": (primary.page_url or primary.url) if primary else None,
            "previous_attempt_failed": failure,
            # The rescue sees two pictures: the page now (first image) and the
            # page the failed attempt left behind (second), named here so the
            # model knows which is which.
            "previous_attempt_left": None
            if failed_look is None
            else {
                "url": failed_look.url,
                "screen_text": failed_look.digest,
                # Named by position: second when the page as it is now was
                # photographed too, the only image when it was not.
                "screenshot": None
                if not failed_look.screenshot
                else ("the second image" if look.screenshot else "the only image"),
            },
        },
        indent=2,
        # The redaction marker is «redacted»; the default ensure_ascii would
        # write it into the prompt in a form nothing else in this system uses.
        ensure_ascii=False,
    )
    answer = await asker.ask(
        model=model,
        instructions=PLAN_INSTRUCTIONS,
        evidence=evidence,
        schema=PLAN_SCHEMA,
        image=look.screenshot,
        images=(failed_look.screenshot,) if failed_look and failed_look.screenshot else (),
        effort=effort,
    )
    if answer.data is None or primary is None:
        return Planned("none", {}, answer.error or "no evidence to act on", answer)

    data = answer.data
    kind = data.get("kind")
    why = str(data.get("why") or "")
    if kind not in KINDS:
        return Planned(
            "none", {}, f"the model planned a command the protocol does not have: {kind!r}", answer
        )

    if kind == "navigate":
        url = data.get("url")
        if not isinstance(url, str) or not url:
            return Planned("none", {}, "navigate with no url", answer)
        return Planned(
            "navigate", {"url": url, "origin": origin, "allow_focus": allow_focus}, why, answer
        )

    if kind == "http.send":
        call = recorded_call(step, {gesture.id: gesture for gesture in cited})
        if call is None:
            return Planned(
                "none", {}, "http.send planned for a step whose evidence carries no call", answer
            )
        if unreplayable(call):
            # Falls through to the ui.perform below rather than returning
            # "none": a step the operator performed by clicking Save is still
            # performable by clicking Save, and planning nothing burns it.
            why = f"recorded call is not replayable; {why}"
        else:
            body = call.request_body.text if call.request_body and call.request_body.text else None
            return Planned(
                "http.send",
                {
                    "method": call.method.upper(),
                    "url": call.url,
                    "headers": headers_without_markers(call.request_headers),
                    "body": body,
                },
                why,
                answer,
            )

    # Both the plan the model asked for and the one it gets when its http.send
    # cannot be replayed. One path, so the downgrade cannot drift from the plan
    # it is downgrading to.
    action = data.get("action") if data.get("action") in ACTIONS else primary.action.kind
    said = data.get("value")
    payload: dict[str, object] = {
        "action": action,
        # str(), because nothing validates the model's answer against the
        # schema: a `"value": 123` otherwise reaches the extension as an int.
        "value": value_for(step, primary, values, None if said is None else str(said))
        if action in VALUED
        else None,
        # The evidence's ladder, never the model's: the model chooses which
        # control the step means, the demonstration says where that control is.
        "locators": [rung.as_payload() for rung in locators_for(primary)],
        "origin": origin,
    }
    if allow_focus:
        payload["allow_focus"] = True
    if starts_on:
        payload["starts_on"] = starts_on
    return Planned("ui.perform", payload, why, answer)


async def plan_by_sight(
    *,
    step: Step,
    cited: list[Gesture],
    values: Mapping[str, str],
    look: Look,
    origin: str | None,
    asker: Asker,
    model: str,
    failure: str | None,
) -> Planned:
    """The rung below the locator ladder: find the control by looking.

    Asked once, after both evidence rungs missed with `control_not_found`, and
    only with a picture to look at. The answer is a point, sent as
    `ui.perform_at`; the runner records the step matched by sight and marks the
    job stale, the same instinct as `css_path` catching what `component` and
    `role_and_name` missed -- one rung lower down."""
    primary = _primary(step, cited)
    if look.screenshot is None or not look.width or not look.height:
        return Planned("none", {}, "no screen to look at", Answer())
    if primary is None:
        return Planned("none", {}, "no evidence to act on", Answer())
    evidence = json.dumps(
        {
            "step": {"order": step.order, "says": step.says, "parameters": step.parameters},
            "demonstrated_on": trim(primary),
            "values": dict(values),
            "browser": {"url": look.url, "screen_text": look.digest},
            "viewport": {"width": look.width, "height": look.height},
            "previous_attempt_failed": failure,
        },
        indent=2,
        ensure_ascii=False,
    )
    answer = await asker.ask(
        model=model,
        instructions=SIGHT_INSTRUCTIONS,
        evidence=evidence,
        schema=SIGHT_SCHEMA,
        image=look.screenshot,
    )
    data = answer.data
    if data is None:
        return Planned("none", {}, answer.error or "no answer", answer)
    why = str(data.get("why") or "")
    if not data.get("found"):
        return Planned("none", {}, why or "the control is not on this screen", answer)
    x, y = data.get("x"), data.get("y")
    # Inside the picture, or nowhere: a point off the viewport is a guess.
    if not (
        isinstance(x, int) and isinstance(y, int) and 0 <= x < look.width and 0 <= y < look.height
    ):
        return Planned("none", {}, f"the point ({x}, {y}) is not on the screen", answer)
    # Nothing validates the model's answer against the schema; the enum is
    # checked here, as `plan_step` checks its own.
    action = data.get("action")
    if action not in SIGHT_ACTIONS:
        return Planned("none", {}, f"{action!r} is not an action a point can take", answer)
    payload: dict[str, object] = {"origin": origin, "x": x, "y": y, "action": action}
    if action == "type":
        said = data.get("value")
        value = value_for(step, primary, values, str(said) if said is not None else None)
        if value is None:
            return Planned("none", {}, "nothing to type: no value for this control", answer)
        payload["value"] = value
    return Planned("ui.perform_at", payload, why, answer)
