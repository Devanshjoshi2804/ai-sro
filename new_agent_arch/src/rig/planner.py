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
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from rig.locators import locators_for, recorded_call
from rig.models import Answer, Asker, Effort
from rig.records import Gesture
from rig.trim import is_secret, trim
from rig.wire import REDACTED, Body, headers_without_markers
from rig.workflows import Step

KINDS = frozenset({"ui.perform", "http.send", "navigate"})
ACTIONS = frozenset({"click", "type", "select", "press", "upload", "scroll", "hover"})

PLAN_SCHEMA: dict[str, Any] = {
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

INSTRUCTIONS = """You are performing one step of a job an operator demonstrated in a warehouse
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


@dataclass(frozen=True, slots=True)
class Planned:
    kind: str
    payload: dict[str, Any]
    why: str
    answer: Answer


def _value_for(
    step: Step, gesture: Gesture, values: Mapping[str, str], said: str | None
) -> str | None:
    """The run's value for this control, else what the model said, else what
    was recorded. The run's values win: they are what the person asked for.

    A credential is never filled in from anywhere. `wire.Gesture` already nulls
    the value at parse time when either secret flag is set, so this is the same
    second belt `trim.is_secret` wears -- and for the same reason: that
    validator does not re-run if a nested Target is mutated afterwards.
    """
    if is_secret(gesture):
        return None
    target = gesture.gesture.target
    component = target.component if target else None
    for name in (
        component.itemId if component else None,
        component.fieldLabel if component else None,
        target.name if target else None,
        *step.parameters,
    ):
        if name and name in values:
            return values[name]
    if said:
        return said
    return gesture.gesture.value


def _unreplayable(body: Body | None) -> bool:
    """Whether replaying this call would send something other than what the
    operator sent.

    A dropped header is survivable -- the page can mint a fresh CSRF token, and
    that is the whole argument for preferring `ui.perform`. A dropped body is
    not: the call would arrive with the marker in it, or with nothing where the
    payload was, and the store would write half a record. Two ways the text is
    gone: it was never kept (`blob_uri`, `redacted_fields` -- the body was
    offloaded or declined) or it was kept with a credential struck out of it.

    No body at all is not unreplayable. There is nothing to get wrong.
    """
    if body is None:
        return False
    if body.text is None:
        return bool(body.blob_uri or body.redacted_fields)
    return REDACTED in body.text


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
) -> Planned:
    primary = next((g for g in cited if g.gesture.kind != "scroll"), cited[0] if cited else None)
    evidence = json.dumps(
        {
            "step": {"order": step.order, "says": step.says, "parameters": step.parameters},
            "evidence": [trim(g) for g in cited],
            "values": dict(values),
            "browser": {"url": look.url, "screen_text": look.digest},
            # The real page, not `trim()`'s starred path shape: a step deep in a
            # job was demonstrated on a specific screen, and the planner can only
            # say "navigate there first" if it is told where there is.
            "step_page": (primary.page_url or primary.url) if primary else None,
            "previous_attempt_failed": failure,
        },
        indent=2,
        ensure_ascii=False,
    )
    answer = await asker.ask(
        model=model,
        instructions=INSTRUCTIONS,
        evidence=evidence,
        schema=PLAN_SCHEMA,
        image=look.screenshot,
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
        call = recorded_call(step, {g.id: g for g in cited})
        if call is None:
            return Planned(
                "none", {}, "http.send planned for a step whose evidence carries no call", answer
            )
        if _unreplayable(call.request_body):
            # Falls through to the ui.perform below rather than returning
            # "none": a step the operator performed by clicking Save is still
            # performable by clicking Save, and planning nothing burns it.
            why = f"recorded body is not replayable; {why}"
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
    action = data.get("action") if data.get("action") in ACTIONS else primary.gesture.kind
    said = data.get("value")
    payload: dict[str, Any] = {
        "action": action,
        # str(), because nothing validates the model's answer against the
        # schema: a `"value": 123` otherwise reaches the extension as an int.
        "value": _value_for(step, primary, values, None if said is None else str(said))
        if action in ("type", "select", "upload", "press")
        else None,
        "locators": locators_for(primary),
        "origin": origin,
    }
    if allow_focus:
        payload["allow_focus"] = True
    if starts_on:
        payload["starts_on"] = starts_on
    return Planned("ui.perform", payload, why, answer)
