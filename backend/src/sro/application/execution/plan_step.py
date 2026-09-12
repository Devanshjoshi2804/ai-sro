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

That preference was measured, not assumed. Blue Yonder signs every write with a
`CSRF-ENCRYPT-TOKEN` header and the rig strikes it out at its boundary:
`sro.domain.recording.sensitivity` is the rule that classifies it, and
`test_an_http_plan_replays_the_recorded_call_with_redacted_headers_dropped` is
what holds this module to it. An `http.send` replaying the recorded call would
send the marker as its token and be refused; clicking Save lets the page mint
its own. So `http.send` is for a step whose evidence carries a call and no
usable target -- and a struck-out header is never sent as its marker under
any plan.

One narrow exception, and it is opt-in per call: `verified_writes` -- see
`sro.domain.execution.verified_writes` -- is a ledger of `(method, path)`
pairs this deployment has individually watched succeed, edit, verify, revert.
For a call that matches one, a header the extension itself has a live source
for (today, only `CSRF-ENCRYPT-TOKEN`) is named in the plan's `live_headers`
rather than left off; the extension fetches the value off the page it is
already in, and it is never carried on the wire from here. Everything else --
an unverified call, or a header the extension has no live source for -- keeps
the rule above exactly as it was.

An instance count of those headers used to stand here in place of the name. It
was taken over a capture store that was a scratchpad and is gone, nothing in
this repository reproduces it, and the rule does not rest on it -- so it is the
header and its guard that are cited instead.
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
    LIVE_FETCHABLE_HEADERS,
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
from sro.domain.execution.verified_writes import VerifiedWrite, verified_write_for
from sro.domain.observation.gesture import Gesture, Kind
from sro.domain.observation.trim import trim
from sro.domain.shared.hosts import REDACTED
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
    verified_writes: tuple[VerifiedWrite, ...] = (),
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
            payload: dict[str, object] = {
                "method": call.method.upper(),
                "url": call.url,
                "headers": headers_without_markers(call.request_headers),
                "body": body,
            }
            # A struck-out header is not sent as its marker -- that much holds
            # for every call. For a call this deployment has individually
            # watched succeed (`verified_write_for`), a header the extension
            # itself knows a live source for is asked for instead of being
            # left off: dropping `CSRF-ENCRYPT-TOKEN` sends a Blue Yonder
            # write the app will refuse before routing it, the third 404 shape
            # `knowledge-base/KNOWLEDGE-BASE.md` names. Named, not sent: the
            # extension fetches the value itself, off the page it is already
            # in, and it never reaches the backend at all.
            if verified_write_for(call, verified_writes) is not None:
                live = [
                    name
                    for name, value in call.request_headers.items()
                    if REDACTED in value and name.lower() in LIVE_FETCHABLE_HEADERS
                ]
                if live:
                    payload["live_headers"] = live
            return Planned("http.send", payload, why, answer)

    # Both the plan the model asked for and the one it gets when its http.send
    # cannot be replayed. One path, so the downgrade cannot drift from the plan
    # it is downgrading to.
    action = data.get("action") if data.get("action") in ACTIONS else primary.action.kind
    said = data.get("value")
    # A step that was asked for a value and is about to be performed by an
    # action that cannot carry one. `VALUED` says a click types nothing, so the
    # value is dropped here and the command goes out carrying the locators of
    # whatever the RECORDING clicked -- the run creates the record with the
    # demonstrated choice, the save returns 2xx, and `verify` holds it by
    # status. The operator asked for ENVEYO and got ConnectShip (TanData), and
    # nothing anywhere says so.
    #
    # `undeliverable` exists for this failure and cannot see this route: it
    # asks whether `value_for` would FIND the name, and here it does -- through
    # `step.parameters` -- and the plan then throws the answer away. Nor can it
    # be decided when the job is mined: the action is the model's to choose at
    # plan time, so a step whose recorded gesture is a click is routinely
    # planned as a `type` and delivers its value perfectly well. The only
    # moment the truth is known is this one.
    #
    # Real, and in the store: acme's `Create a Carrier Cross Reference` is done
    # entirely with dropdowns -- every cited gesture is a click with no value
    # -- and declares `Carrier`, `Service Level` and `External System Name`.
    # `StartWorkflowRun` refuses a press that leaves a declared parameter
    # empty, so the operator is made to supply all three, and a click step
    # cannot apply any of them.
    #
    # Refused rather than logged. A job that stops and says why costs an
    # operator a minute; a job that writes the wrong carrier into a warehouse
    # and reports success costs somebody a day finding it.
    if action not in VALUED:
        asked = [name for name in step.parameters if name in values]
        if asked:
            return Planned(
                "none",
                {},
                f"step {step.order} was given {', '.join(sorted(asked))} and a "
                f"{action} cannot carry a value: choosing from a list by value "
                "is not implemented, and performing this step would use the "
                "recorded choice instead of the one asked for",
                answer,
            )
    payload = {
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
