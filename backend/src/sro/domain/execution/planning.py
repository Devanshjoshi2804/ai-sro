"""Flash plans exactly one command for one step.

The model answers a small shape -- which kind of command, which action, which
value, which url -- and the rig assembles the payload. The locators never come
from the model: they are A13's, built from the cited evidence, and the
extension tries them in order. What the model decides is only what to do with
them, and it is told to prefer driving the interface over replaying a call.

That preference was measured, not assumed. 544 of the real store's request
headers are CSRF tokens, every one redacted at the rig's boundary. An
`http.send` replaying the recorded call would send the marker as its token and
be refused; clicking Save lets the page mint its own. So `http.send` is for a
step whose evidence carries a call and no usable target -- and a header whose
stored value is the redaction marker is never sent under any plan.

The two functions that call the model (`plan_step`, `plan_by_sight`) are not
here: this module is the pure half -- the schemas, the instructions, the value
rule and the replayability rule -- which is everything a test can pin without
a model behind it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sro.domain.observation.gesture import Call, Gesture
from sro.domain.observation.trim import is_secret
from sro.domain.shared.hosts import REDACTED
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step

KINDS = frozenset({"ui.perform", "http.send", "navigate"})

PLAN_SCHEMA: dict[str, object] = {
    "type": "object",
    # kind first, why last: decide, then explain.
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
    # The CSS viewport the picture shows, which is the space `ui.perform_at`
    # acts in. Zero when the browser gave no picture.
    width: int = 0
    height: int = 0


@dataclass(frozen=True, slots=True)
class Planned:
    kind: str
    payload: dict[str, object]
    why: str
    answer: Answer


def value_for(
    step: Step, gesture: Gesture, values: Mapping[str, str], said: str | None
) -> str | None:
    """The run's value for this control, else what the model said, else what
    was recorded. The run's values win: they are what the person asked for.

    A credential is never filled in from anywhere. The wire parser already nulls
    the value at parse time when either secret flag is set, so this is the same
    second belt `trim.is_secret` wears -- and for the same reason: that
    validator does not re-run if a nested Target is mutated afterwards.
    """
    if is_secret(gesture):
        return None
    target = gesture.action.target
    component = target.component if target else None
    for name in (
        component.item_id if component else None,
        component.field_label if component else None,
        target.name if target else None,
        *step.parameters,
    ):
        if name and name in values:
            return values[name]
    if said:
        return said
    return gesture.action.value


def unreplayable(call: Call) -> bool:
    """Whether replaying this call would send something other than what the
    operator sent.

    A dropped header is survivable -- the page can mint a fresh CSRF token, and
    that is the whole argument for preferring `ui.perform`. A dropped body is
    not: the call would arrive with the marker in it, or with nothing where the
    payload was, and the store would write half a record. Two ways the text is
    gone: it was never kept (`blob_uri`, `redacted_fields` -- the body was
    offloaded or declined) or it was kept with a credential struck out of it.

    No body at all is not unreplayable. There is nothing to get wrong.

    The url gets the same rule as the body. `redact_url` strikes a credential
    out of a query string at parse, and the one such call in the real store is
    an analytics beacon carrying a cookie as a parameter: replayed, it would
    send the marker's own text where the cookie was.
    """
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
        # No select: `performAtInPage` has no way to choose an option at a
        # point, and an action the browser cannot take is a step that stops.
        "action": {"type": "string", "enum": ["click", "type", "press"]},
        "value": {"type": "string", "nullable": True},
        "why": {"type": "string"},
    },
    "required": ["found", "x", "y", "action", "why"],
    "propertyOrdering": ["found", "x", "y", "action", "value", "why"],
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
If the control is not on this screen, answer found: false and say why. Never
guess a point: a click on the wrong control in a warehouse system is worse
than a step that stops and asks."""
