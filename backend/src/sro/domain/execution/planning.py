from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from sro.domain.execution.evidence import control_names
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.observation.trim import is_secret
from sro.domain.shared.hosts import REDACTED
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step

KINDS = frozenset({"ui.perform", "http.send", "navigate"})

COMMAND_KINDS = KINDS | frozenset(
    {"ui.perform_at", "ui.url", "screenshot", "abort", "tab.open", "calls.since", "sign_in"}
)

LIVE_FETCHABLE_HEADERS = frozenset({"csrf-encrypt-token", "x-requested-with"})

PLAN_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["ui.perform", "http.send", "navigate"]},
        "action": {
            "type": "string",
            "nullable": True,
            "enum": ["click", "type", "select", "press", "upload", "scroll", "hover"],
        },
        "value": {"type": "string", "nullable": True},
        "url": {"type": "string", "nullable": True},
        "why": {"type": "string"},
    },
    "required": ["kind", "why"],
    "propertyOrdering": ["kind", "action", "value", "url", "why"],
}

PLAN_INSTRUCTIONS = """You are performing one step of a job an operator demonstrated in a warehouse
system, in their own browser. You are given the step's sentence, the evidence
it was read from (the gesture the operator made and any calls the page sent),
the values this run was given, and where the browser is now.

Plan exactly ONE command:
- ui.perform: act on the control the evidence points at. Give the action and,
  for type/select/upload, the value from this run's values. Prefer this.
- http.send: only when the evidence carries a call and there is no usable
  control to drive. The call itself is taken from the evidence.
- navigate: only when the browser is on the wrong page for this step -- compare
  `browser.url` with `step_page`, the screen this step was demonstrated on.
  Give the url. After a navigate the same step is planned again.

Never invent a control, a url or a value that is not in the evidence or the
run's values. If the step cannot be done from what you are shown, say so in
`why` and choose the kind that gets closest."""


@dataclass(frozen=True, slots=True)
class Look:
    url: str | None
    screenshot: bytes | None
    digest: str
    width: int = 0
    height: int = 0
    refused: str = ""

    elsewhere: str = ""

    elsewhere_is_ours: bool = False

    signed_out: bool = False

    dialog: str = ""

    loading: bool = False


@dataclass(frozen=True, slots=True)
class Planned:
    kind: str
    payload: dict[str, object]
    why: str
    answer: Answer
    opens: bool = False

    rewrote: bool = False

    filled: Mapping[str, str] = MappingProxyType({})

    confirm: Mapping[str, str] = MappingProxyType({})

    by: str = ""


def own_parameter(step: Step, gesture: Gesture) -> str | None:
    named = [name for name in step.parameters if name in control_names(gesture)]
    if named:
        return named[0]
    return step.parameters[0] if len(step.parameters) == 1 else None


def value_for(
    step: Step, gesture: Gesture, values: Mapping[str, str], said: str | None
) -> str | None:
    if is_secret(gesture):
        return None
    target = gesture.action.target
    component = target.component if target else None
    own = own_parameter(step, gesture)
    for name in (
        component.item_id if component else None,
        component.field_label if component else None,
        target.name if target else None,
        own,
    ):
        if name and name in values:
            return values[name]
    if said:
        return said
    return None if step.parameters else gesture.action.value


def shown_after(step: Step, gesture: Gesture, value: str | None) -> str | None:
    after = gesture.action.after
    if value is not None or after is None or step.parameters:
        return value
    return after.value


def unreplayable(call: Call) -> bool:
    if REDACTED in call.url:
        return True
    body = call.request_body
    if body is None:
        return False
    if body.text is None:
        return bool(body.blob_uri or body.redacted_fields)
    return REDACTED in body.text


SIGHT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "found": {"type": "boolean"},
        "x": {"type": "integer"},
        "y": {"type": "integer"},
        "action": {"type": "string", "enum": ["click", "type", "press"]},
        "value": {"type": "string", "nullable": True},
        "points_at": {
            "type": "string",
            "enum": ["the_control", "what_reveals_it", "what_is_in_the_way", "nothing"],
        },
        "why": {"type": "string"},
    },
    "required": ["found", "x", "y", "action", "points_at", "why"],
    "propertyOrdering": ["found", "x", "y", "action", "value", "points_at", "why"],
}

SIGHT_ACTIONS = frozenset({"click", "type", "press"})

SIGHT_INSTRUCTIONS = """You are performing one step of a job an operator demonstrated in a warehouse
system, in their own browser. Every way of finding the control by its recorded
identity has failed: the page has changed under the job. You are shown the
screen as it is now, the step's sentence, what the control looked like when it
was demonstrated, and the values this run was given.

Find the control for THIS step on the screen. Answer its centre in CSS pixels
of the viewport whose size you are given -- the picture is that viewport --
and the action to take there. For type, give the value from this run's values.

Every answer carries one point and says what it points at.

 - the_control: the control for this step. found: true, and the action to take.
 - what_reveals_it: the control is not on this screen, and THIS is the thing
   that would reveal it -- the closed menu it lives under, a collapsed section,
   a tab that is not the open one. It will be clicked and you will be asked
   again with a new picture. found: false.
 - what_is_in_the_way: something is covering the screen and has to be dismissed
   before anything under it can be used -- a dialog, an alert, a notice with an
   OK or a Close. Point at the button that dismisses it. Warehouse systems put
   one of these in front of a page for things that are not errors at all: a
   dialog headed "Exception Occurred" whose text is "Processing completed
   without exception" is one this system has met. found: false.
 - nothing: the control is not here and nothing on this screen leads to it.
   found: false, and the point is ignored.

Dismissing a dialog is not doing the step, and neither is opening a menu: in
both cases you will be asked again with a new picture, and the step is what you
answer then.

Saying "it is probably under the Partners menu" and pointing at nothing is an
answer nobody can act on. If you can name the menu you can point at it, and
pointing is what moves the job. Only point at what you can SEE: opening a menu
is not doing the step, and a click on something else to find out what happens
is exactly what this rung must not do.

Never guess a point: a click on the wrong control in a warehouse system is
worse than a step that stops and asks."""
