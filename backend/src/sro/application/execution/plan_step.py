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
from collections.abc import Awaitable, Callable, Mapping
from types import MappingProxyType
from typing import get_args

from sro.application.capture.rig_wire import headers_without_markers
from sro.application.ports.model import Asker
from sro.domain.execution.evidence import (
    Locator,
    locators_for,
    primary_gesture,
    recorded_call,
    writes,
)
from sro.domain.execution.learned_step import LearnedStep
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
from sro.domain.execution.secrets import field_of, needs_a_secret, secret_key_for
from sro.domain.execution.verified_writes import VerifiedWrite, verified_write_for
from sro.domain.execution.write_plan import WritePlan, wanted_by, write_plan_for
from sro.domain.observation.gesture import Gesture, Kind
from sro.domain.observation.trim import trim
from sro.domain.shared.hosts import REDACTED, origin_of
from sro.domain.shared.prices import Answer, Effort
from sro.domain.skill.workflow import Step

SecretFor = Callable[[str], Awaitable[str | None]]
"""Where a password comes from when a step types one: the vault, by key.

A callable rather than the vault itself, so this module -- which builds one
command out of one step -- does not learn what a vault is. `run_workflow` holds
the real one; a run with no vault configured passes nothing, and a step that
needs a password says so rather than typing a blank."""

ACTIONS: frozenset[str] = frozenset(get_args(Kind))
"""What a `ui.perform` may ask for: the gesture kinds the recorder records, and
no others. One list, because a plan the extension is asked to perform is a
gesture the recorder could have seen -- `PLAN_SCHEMA` offers the model exactly
these, and `test_the_actions_offered_are_the_actions_accepted` fails if the two
ever part."""

VALUED = ("type", "select", "upload", "press")
"""The actions that carry a value. A click types nothing."""


def _replay_of(
    step: Step,
    by_id: Mapping[str, Gesture],
    values: Mapping[str, str],
    verified_writes: tuple[VerifiedWrite, ...],
    seen: Mapping[str, frozenset[str]],
) -> tuple[dict[str, object], WritePlan | None] | None:
    """The recorded call as a payload, re-aimed at this run's values, and the
    plan that aimed it. `None` where it must not go out as it stands.

    Two refusals, and they are different failures. A call is `unreplayable`
    when its recorded bytes cannot be sent at all. A call is un-AIMABLE when
    this run was given values, the call is one the ledger has watched succeed,
    and `write_plan_for` could not work out which of its fields the values
    belong in -- sending it then would send the DEMONSTRATION's values, so the
    operator asks for `GPDP` and the warehouse is told `GGD` and answers 201
    for it.

    Gated on the LEDGER, and that is what makes the second refusal narrow
    enough to be right. A run holds its values for the whole job, so "this run
    has values" says nothing about whether a given call carries any of them,
    and refusing on that alone turned every replay into a click. It also
    catches what inspecting the body cannot: the ledger's own gotcha is
    `csttyp truncates at 4 chars`, so the operator typed `ZV9680`, the body
    went out as `ZV96`, and no value in the body equals anything anybody was
    seen typing.

    Both callers are here -- the model's `http.send` and the replay the
    evidence decides on its own -- so what goes on the wire cannot differ by
    who asked for it.
    """
    call = recorded_call(step, by_id)
    if call is None or unreplayable(call):
        return None
    verified = verified_write_for(call, verified_writes) is not None
    aimed = write_plan_for(step, by_id, values, verified_writes, seen)
    if aimed is None and values and verified:
        return None
    # And the same refusal for a run that was given NOTHING.
    #
    # The guard above asks "were we handed values we could not place", which a
    # run holding none can never fail -- so the one case where replaying the
    # recording is most certainly wrong was the one case it let through.
    # Measured on the deployment 2026-09-16: an operator pressed a card, the
    # gather came back empty because the model answered one round with a 5xx,
    # and the run replayed the demonstration's own body -- the code somebody
    # typed days ago, into a warehouse, as if it had been asked for today.
    #
    # `wanted_by` asks the question without the values: which parameters does
    # THIS call's body carry. A call that carries none still replays exactly as
    # it was demonstrated, which is what most calls are and what they have
    # always done.
    if verified and any(not values.get(name, "").strip() for name in wanted_by(step, by_id, seen)):
        return None
    # `aimed` where there is one, and the recorded bytes where there is nothing
    # to aim -- a job with no parameters replays exactly as it was
    # demonstrated, which is what it has always done and what most calls still
    # are.
    recorded = call.request_body.text if call.request_body else None
    payload: dict[str, object] = {
        "method": call.method.upper(),
        "url": call.url,
        "headers": headers_without_markers(call.request_headers),
        "body": aimed.body if aimed is not None else (recorded or None),
    }
    # A struck-out header is not sent as its marker -- that much holds for
    # every call. For a call this deployment has individually watched succeed,
    # a header the extension itself knows a live source for is asked for
    # instead of being left off: dropping `CSRF-ENCRYPT-TOKEN` sends a Blue
    # Yonder write the app will refuse before routing it, the third 404 shape
    # `knowledge-base/KNOWLEDGE-BASE.md` names. Named, not sent: the extension
    # fetches the value itself, off the page it is already in, and it never
    # reaches the backend at all.
    if verified:
        live = [
            name
            for name, value in call.request_headers.items()
            if REDACTED in value and name.lower() in LIVE_FETCHABLE_HEADERS
        ]
        if live:
            payload["live_headers"] = live
    return payload, aimed


def replay_without_asking(
    *,
    step: Step,
    cited: list[Gesture],
    values: Mapping[str, str],
    verified_writes: tuple[VerifiedWrite, ...],
    seen: Mapping[str, frozenset[str]] = MappingProxyType({}),
    starts_on: str | None = None,
) -> Planned | None:
    """The one command a step can be planned without asking anybody.

    The evidence says which call the step made, `write_plan_for` says where
    this run's values go in it, and the ledger says this deployment has already
    watched that `(method, path)` succeed. Nothing is left for a model to
    decide, so nothing is asked -- and that is worth more than the vision call
    it saves. A step planned by a model is planned again from scratch every
    run: the same job sends `http.send` on Tuesday and clicks Save on
    Wednesday, and the one step that changes warehouse state is the one where
    that matters. Deterministic where the evidence is complete, a model only
    where it is not.

    Narrow on purpose. Only a call already in the ledger, which is the same
    gate `live_headers` sits behind -- and the same reason: an unverified write
    replayed from a recording sends a struck-out `CSRF-ENCRYPT-TOKEN` and is
    refused, so the module's standing preference for driving the interface is
    exactly right for every call this does not cover.

    The rescue still asks. A replay that failed by status is precisely when
    clicking Save is the right next move, and `run_workflow` puts this first in
    the ladder rather than in place of it.
    """
    by_id = {gesture.id: gesture for gesture in cited}
    call = recorded_call(step, by_id)
    if call is None or verified_write_for(call, verified_writes) is None:
        return None
    sending = _replay_of(step, by_id, values, verified_writes, seen)
    if sending is None:
        return None
    payload, aimed = sending
    if starts_on:
        # The page this call may open a tab at, and only ever for the run's
        # first command -- `run_workflow` passes it for that one alone.
        #
        # An `http.send` never carried this before because it never needed to:
        # the steps that walked the browser to the form ran first and left a
        # tab on the origin. A job whose write goes out as a call performs none
        # of them, so this IS the first command, and the session it needs lives
        # in that origin's cookies. `opensFor` in `commands.js` still refuses a
        # `starts_on` naming another system, so this can only open the page the
        # call is going to.
        payload["starts_on"] = starts_on
    return Planned(
        "http.send",
        payload,
        "the evidence records this call and the ledger has watched it succeed",
        Answer(),
        rewrote=aimed is not None,
        filled=dict(aimed.filled) if aimed is not None else {},
        confirm=dict(aimed.confirm) if aimed is not None else {},
        by="evidence",
    )


def _primary(step: Step, cited: list[Gesture]) -> Gesture | None:
    """The gesture this step is planned from.

    `primary_gesture` prefers one the extension can act on and so skips a
    scroll -- but a step citing nothing else is not a step to give up on, and
    falls back to the first cited gesture rather than planning nothing.
    """
    found = primary_gesture(step, {gesture.id: gesture for gesture in cited})
    return found or (cited[0] if cited else None)


def _ladder(primary: Gesture, learned: LearnedStep | None) -> list[Locator]:
    """The demonstration's ladder, with what a run learned on top.

    Never instead: the recorded identity stays underneath, because a page that
    is repaired tomorrow should go back to being found the strong way, and a
    learned locator that has itself gone stale is one rung that misses rather
    than a step with nothing to try.
    """
    rungs = locators_for(primary)
    if learned is None or not learned.usable:
        return rungs
    first = Locator(learned.strategy, learned.query, visible_only=True)
    return [first, *[rung for rung in rungs if rung.as_payload() != first.as_payload()]]


def _clicking(
    ladder: list[Locator], origin: str | None, allow_focus: bool, starts_on: str | None
) -> dict[str, object]:
    """A click on the control this ladder names, carrying no value."""
    payload: dict[str, object] = {
        "action": "click",
        "value": None,
        "locators": [rung.as_payload() for rung in ladder],
        "origin": origin,
    }
    if allow_focus:
        payload["allow_focus"] = True
    if starts_on:
        payload["starts_on"] = starts_on
    return payload


async def plan_step(
    *,
    step: Step,
    learned: LearnedStep | None = None,
    cited: list[Gesture],
    values: Mapping[str, str],
    look: Look,
    origin: str | None,
    starts_on: str | None,
    allow_focus: bool,
    asker: Asker,
    model: str,
    opened: bool = False,
    effort: Effort | None = None,
    failure: str | None = None,
    failed_look: Look | None = None,
    verified_writes: tuple[VerifiedWrite, ...] = (),
    seen: Mapping[str, frozenset[str]] = MappingProxyType({}),
    tenant_id: str = "",
    secret_for: SecretFor | None = None,
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
        by_id = {gesture.id: gesture for gesture in cited}
        call = recorded_call(step, by_id)
        if call is None:
            return Planned(
                "none", {}, "http.send planned for a step whose evidence carries no call", answer
            )
        sending = _replay_of(step, by_id, values, verified_writes, seen)
        if sending is not None:
            payload, aimed = sending
            if starts_on:
                # Same as the deterministic replay below, and for the same
                # reason. `run_workflow` passes this for the run's FIRST
                # command only, so a model that chooses a call for the step a
                # run begins at can open the page it needs -- a resumed run
                # lands on one of those, and without this it answers
                # `no_tab_for_origin` to an operator who has no tab there.
                payload["starts_on"] = starts_on
            return Planned(
                "http.send",
                payload,
                why,
                answer,
                rewrote=aimed is not None,
                filled=dict(aimed.filled) if aimed is not None else {},
                confirm=dict(aimed.confirm) if aimed is not None else {},
            )
        if unreplayable(call):
            # Falls through to the ui.perform below rather than returning
            # "none": a step the operator performed by clicking Save is still
            # performable by clicking Save, and planning nothing burns it.
            why = f"recorded call is not replayable; {why}"
        elif values and verified_write_for(call, verified_writes) is not None:
            # The run was given values and nothing could work out where they go.
            # Sending the recorded body would send the DEMONSTRATION's values --
            # the operator asks for `GPDP` and the warehouse is told `GGD`, and
            # answers 201 for it. So this falls through the same way an
            # unreplayable body does, to the interface where the values reach
            # the form through `value_for` as they always have.
            #
            # Gated on the LEDGER, and that is what makes it narrow enough to
            # be right. A run holds its values for the whole job, so "this run
            # has values" says nothing about whether a given call carries any
            # of them, and falling through on that alone turned every replay
            # into a click. A `(method, path)` this deployment has individually
            # watched succeed is a real state change, and one this run cannot
            # aim is the one place a stale value costs a record.
            #
            # It also catches what inspecting the body cannot. The ledger's own
            # gotcha is `csttyp truncates at 4 chars`: the operator typed
            # `ZV9680`, the body went out as `ZV96`, and no value in the body
            # equals anything anybody was seen typing. A rule that looked for
            # the demonstrated value inside the bytes would find nothing and
            # send the truncation.
            why = f"the recorded body cannot be re-aimed at this run's values; {why}"

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
    #
    # Two clicks are how a person answers one of these, and two clicks are how
    # this does it. `opened` says which half is being planned: the first sends
    # the demonstrated click, which opens the list and answers nothing, and the
    # second clicks the row whose text IS the value asked for. Nothing is
    # guessed -- the row is named by the operator's own answer, so a control
    # carrying that text either exists on the page or the browser says
    # `control_not_found` and the step fails, which is where the refusal below
    # left it anyway.
    #
    # Only for a step that changes nothing. The opening click goes out from
    # inside the planning loop, ahead of the gate that withholds a write from a
    # dry run and parks one on a person -- the same place `navigate` already
    # sends from, and safe there for the same reason: opening a list, like
    # going to a page, is not the writing.
    if action not in VALUED:
        asked = sorted(name for name in step.parameters if name in values)
        wanted = values[asked[0]] if asked else ""
        if asked and not writes(step, {gesture.id: gesture for gesture in cited}):
            if not opened:
                return Planned(
                    "ui.perform",
                    _clicking(locators_for(primary), origin, allow_focus, starts_on),
                    f"opening the list so {asked[0]} can be chosen by value",
                    answer,
                    opens=True,
                )
            return Planned(
                "ui.perform",
                _clicking(
                    [Locator("text", wanted, visible_only=True)], origin, allow_focus, starts_on
                ),
                f"choosing {wanted} from the open list",
                answer,
            )
        if asked:
            return Planned(
                "none",
                {},
                f"step {step.order} was given {', '.join(asked)} and a "
                f"{action} cannot carry a value: this step also writes, so the "
                "list cannot be opened first, and performing it would use the "
                "recorded choice instead of the one asked for",
                answer,
            )
    # A control the recording was never allowed to keep a value for. The value
    # comes from the vault at this moment, by a key built from the system and
    # the field's own name -- never from the evidence, which still holds
    # nothing but the fact that there was a password here.
    #
    # An absent secret is a refusal with the key in it, not a blank typed into
    # a login form: a blank submits, fails, and looks to everybody like the job
    # being broken.
    secret = None
    if action in VALUED and needs_a_secret(primary):
        if secret_for is None:
            return Planned(
                "none",
                {},
                f"step {step.order} types a password and this run has no vault to ask",
                answer,
            )
        wanted = secret_key_for(tenant_id or "", primary)
        secret = await secret_for(wanted)
        if not secret:
            # The refusal carries what it wanted as STRUCTURE and not only as
            # prose. The operator who has to fix this is a person in a
            # warehouse with a panel open: they have no console, no shell and
            # no reason to know what a vault key is, so the panel has to be
            # able to draw "this job needs your password for <system>" and a
            # box -- which it cannot do by parsing a sentence.
            return Planned(
                "none",
                {
                    "needs_secret": {
                        "system": origin_of(primary.url or "") or (primary.system or ""),
                        "field": field_of(primary),
                        "key": wanted,
                    }
                },
                f"step {step.order} types a password and nothing is stored under {wanted!r}",
                answer,
            )

    payload = {
        "action": action,
        # str(), because nothing validates the model's answer against the
        # schema: a `"value": 123` otherwise reaches the extension as an int.
        "value": secret
        if secret is not None
        else value_for(step, primary, values, None if said is None else str(said))
        if action in VALUED
        else None,
        # The evidence's ladder, never the model's: the model chooses which
        # control the step means, the demonstration says where that control is.
        #
        # With what a previous run FOUND at the top of it, where one did. The
        # demonstration's own identity for this control has already failed at
        # least once by then -- that is the only way anything gets written
        # there -- and the locator that worked instead costs a DOM query to
        # try. Measured on the deployment, 2026-09-17: three runs in one
        # afternoon each spent two model calls and a screenshot re-deriving
        # that the control is called "Customer Types".
        "locators": [rung.as_payload() for rung in _ladder(primary, learned)],
        "origin": origin,
    }
    if allow_focus:
        payload["allow_focus"] = True
    if starts_on:
        payload["starts_on"] = starts_on
    return Planned("ui.perform", payload, why, answer)


def _point_on(said: object, look: Look) -> tuple[int, int] | None:
    """A point the model gave, if it is inside the picture it was shown.

    Off the viewport is a guess, and this rung's whole rule is that it does not
    guess: the picture IS the viewport, so a point outside it was not seen.
    """
    if not isinstance(said, dict) or not look.width or not look.height:
        return None
    x, y = said.get("x"), said.get("y")
    if not (isinstance(x, int) and isinstance(y, int)):
        return None
    return (x, y) if 0 <= x < look.width and 0 <= y < look.height else None


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
    opened: bool = False,
) -> Planned:
    """The rung below the locator ladder: find the control by looking.

    Asked once, after both evidence rungs missed with `control_not_found`, and
    only with a picture to look at. The answer is a point, sent as
    `ui.perform_at`; the runner records the step matched by sight and marks the
    job stale, the same instinct as `css_path` catching what `component` and
    `role_and_name` missed -- one rung lower down."""
    primary = _primary(step, cited)
    if look.screenshot is None or not look.width or not look.height:
        # With the browser's own reason, where it gave one. "no screen to look
        # at" alone is the same sentence for a refused focus, a tab that went
        # away and a picture of zero size, and a step that fails for a reason
        # nobody can read is a step nobody can fix.
        why = f"no screen to look at: {look.refused}" if look.refused else "no screen to look at"
        return Planned("none", {}, why, Answer())
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
    points_at = str(data.get("points_at") or "")
    # The enum decides, where the model answered one. `found` is the older
    # question and still the fallback: a deployment pinned to an earlier model
    # answers without `points_at` at all, and its answers still mean what they
    # always did.
    found = points_at == "the_control" if points_at else bool(data.get("found"))
    if not found:
        # Not on the screen, and something on the screen would reveal it.
        #
        # Measured on the deployment, 2026-09-17: the step clicks the "Customer
        # Types" tab, and this rung answered "not currently visible ... it is
        # likely under the 'Partners' menu which needs to be opened first" --
        # the right answer, as prose, with no way to act on it. The job then
        # ran by its call, which is the fallback and not the point: a job whose
        # write has no call would have stopped there holding the fix.
        #
        # The same two-click shape a dropdown already uses: this one opens, the
        # runner plans again with a fresh picture, and the second answers the
        # step. `opened` is the runner's guard, so a planner that only ever
        # opens things spends its budget rather than looping.
        # The point it just gave, when it says that point opens the way.
        # `opened` no longer means "already opened once, so stop". The runner
        # bounds how many things one rung may open (`K_OPENINGS`) and refuses
        # the rest; what this rung must not do is keep pointing at the same
        # thing, which the fresh picture it is shown each time is what settles.
        # Two ways a screen is not ready for the step, and one answer to both:
        # click it and look again. A menu to open is the control being
        # somewhere else; a dialog to dismiss is something on top of it.
        clearing = points_at in ("what_reveals_it", "what_is_in_the_way")
        reveal = _point_on({"x": data.get("x"), "y": data.get("y")}, look) if clearing else None
        if reveal is not None:
            return Planned(
                "ui.perform_at",
                {"origin": origin, "x": reveal[0], "y": reveal[1], "action": "click"},
                (
                    f"clearing what is in the way: {why}"
                    if points_at == "what_is_in_the_way"
                    else f"opening what the control is under: {why}"
                )
                if why
                else "clearing the way to the control",
                answer,
                opens=True,
            )
        # And whether it pointed at something this rung could not use. The
        # alternative is reading the same prose twice and not knowing whether
        # the model would not point or pointed off the picture.
        offered = {"x": data.get("x"), "y": data.get("y")} if clearing else None
        refusal = why or "the control is not on this screen"
        if offered is not None and reveal is None:
            refusal = (
                f"{refusal} (it named {offered!r} to open, which is not on the screen it was shown)"
            )
        return Planned("none", {}, refusal, answer)
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
