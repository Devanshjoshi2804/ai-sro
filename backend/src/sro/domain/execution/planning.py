"""Flash plans exactly one command for one step.

The model answers a small shape -- which kind of command, which action, which
value, which url -- and the rig assembles the payload. The locators never come
from the model: they are A13's, built from the cited evidence, and the
extension tries them in order. What the model decides is only what to do with
them, and it is told to prefer driving the interface over replaying a call.

That preference was measured, not assumed. Blue Yonder signs every write with a
`CSRF-ENCRYPT-TOKEN` header and the rig strikes it out at its boundary:
`sro.domain.recording.sensitivity` is the rule that classifies it, and
`test_an_http_plan_replays_the_recorded_call_with_redacted_headers_dropped` is
what holds the planner to it. An `http.send` replaying the recorded call would
send the marker as its token and be refused; clicking Save lets the page mint
its own. So `http.send` is for a step whose evidence carries a call and no
usable target -- and a header whose stored value is the redaction marker is
never sent under any plan.

An instance count of those headers used to stand here in place of the name. It
was taken over a capture store that was a scratchpad and is gone, nothing in
this repository reproduces it, and the rule does not rest on it -- so it is the
header and its guard that are cited instead.

The two functions that call the model (`plan_step`, `plan_by_sight`) are not
here: this module is the pure half -- the schemas, the instructions, the value
rule and the replayability rule -- which is everything a test can pin without
a model behind it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from sro.domain.observation.gesture import Call, Gesture
from sro.domain.observation.trim import is_secret
from sro.domain.shared.hosts import REDACTED
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step

KINDS = frozenset({"ui.perform", "http.send", "navigate"})
"""What a PLAN may name. The model chooses one of these three."""

COMMAND_KINDS = KINDS | frozenset(
    {"ui.perform_at", "ui.url", "screenshot", "abort", "tab.open", "calls.since"}
)
"""Everything the runner may put on the wire, plan or not.

`KINDS` is the subset a model may choose; the rest the runner sends on its own
-- the sight rung's point (`ui.perform_at`), the two the run asks a browser for
before and after a step (`ui.url`, `screenshot`), the one it asks for the
calls the page made while it was being driven (`calls.since`, which is how a
step performed in a browser can reach the verifier's first rung at all), the
one it sends when a run
is stopped (`abort`), and the one a LOOKUP sends when the system it has to
read is one nobody has open (`tab.open`). Deliberately not in `KINDS`: opening
a tab is never a step of a job, it is what has to be true before a read can
happen at all.

Named here because the other half of this list lives in another language, in
another repository directory, as a `switch` in `commands.js` -- and a kind that
exists on one side only is a command the browser answers `not_actionable` to,
which the run then reads as a step that could not be done. A rule that lives on
two sides of a wire drifts on one of them: `shape_of` served a shape
`recognise.js` could never match for weeks, for exactly this reason.
`test_the_extension_answers_every_command_this_backend_can_send` holds the two
lists together.
"""

LIVE_FETCHABLE_HEADERS = frozenset({"csrf-encrypt-token", "x-requested-with"})
"""Lower-cased header names the extension itself knows how to read off the
live page, rather than out of a recording.

Small and explicit on purpose, the same way `verified_writes.VerifiedWrite`
is: the extension runs whatever JS this list names, so the list is a fixed
menu the extension owns, never a JS snippet the backend sends down the wire
to be run unexamined. Two entries, both read off `Ext.Ajax.defaultHeaders` on
a Blue Yonder page (see `sro.domain.execution.verified_writes`), and a header
this deployment has no live source for is simply never asked for.

`CSRF-ENCRYPT-TOKEN` is a credential and is struck out for that reason.
`X-REQUESTED-WITH` is not one: its value is a fixed marker, and it is struck
out because it sits in `redaction.SECRET_HEADERS` beside the real ones. Either
way the recording carries a marker rather than a value, and a write that
arrives without the header is refused by an application that expects it before
it is ever routed -- so the same mechanism serves both. The alternative was to
stop redacting it, which would have put a value this deployment has no use for
into every stored request; asking the page is the narrower change."""

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
    opens: bool = False
    """This command only opens the control the step answers, and the step is
    not done when it lands. The runner sends it and plans the step again --
    the same shape `navigate` already has, and for the same reason: getting to
    where the answer can be given is not giving it.

    Set for the first half of a pick from a dropdown. See `plan_step`."""

    rewrote: bool = False
    """The recorded body was re-aimed at this run's values rather than replayed
    as it was sent.

    What `verify` reads it for. A 2xx on bytes replayed VERBATIM means the
    demonstrated effect, because the endpoint answered the demonstration the
    same way -- so rung 1 settles the step and rung 2 is never reached. That
    reasoning does not survive a body this run changed: the status then proves
    something was created, not that it carries the values this run was given.

    The instance is in the ledger's own notes. `csttyp truncates at 4 chars`, so
    a create asking for a five-character code is answered **201** and the record
    is four characters long, with nobody told."""

    filled: Mapping[str, str] = MappingProxyType({})
    """Body key -> the parameter whose value now sits there.

    `WritePlan.filled`, carried so the run can ask what is already known about
    the fields it is filling. Empty for every plan that is not a re-aimed
    write. `confirm` below is this narrowed to the slots a read can settle;
    both are needed, and for different questions."""

    confirm: Mapping[str, str] = MappingProxyType({})
    """Body key -> the value this run put there, for the keys a read can settle.

    `WritePlan.confirm`, carried to `verify` so rung 2 can ask whether the
    record holds each value in the slot the plan wrote it to, rather than
    whether the value appears anywhere in the record at all. Empty where the
    plan is not a re-aimed write, and empty where the demonstration shows the
    server rewrites every slot this run filled -- in which case there is
    nothing a read could settle and the status is the whole of the evidence."""

    by: str = ""
    """Who planned it, where that is not the model the runner was about to ask.

    A replay the evidence decides on its own asks nobody, and `planned_by` is
    the one field a reviewer reads to know who to blame for a step. Recording
    a model that was never called there is a lie about the audit trail, and it
    is the kind that survives: the row looks exactly like a step the model got
    right. Empty means the model named at the call site planned it."""


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
        # What would reveal the control, where it is not on the screen at all.
        # Answered INSTEAD of a point, and clicked instead of the step: a
        # closed menu, a collapsed section, a tab that is not the open one.
        "open_first": {
            "type": "object",
            "nullable": True,
            "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
            "required": ["x", "y"],
        },
        "why": {"type": "string"},
    },
    "required": ["found", "x", "y", "action", "why"],
    "propertyOrdering": ["found", "x", "y", "action", "value", "open_first", "why"],
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

If the control is not on this screen, answer found: false and say why.

Then look again for the thing that would reveal it, and if you can see one,
GIVE ITS CENTRE AS open_first. Saying "it is probably under the Partners menu"
and leaving open_first empty is an answer nothing can act on -- if you can name
the menu you can point at it, and pointing is what moves the job. It will be
clicked and you will be asked again with a new picture.

Only something you can SEE on this screen and that plainly reveals the control:
a closed menu it lives under, a collapsed section, a tab that is not the open
one. Opening a menu is not doing the step, and a click on something else to
find out what happens is exactly what this rung must not do.

Never guess a point: a click on the wrong control in a warehouse system is
worse than a step that stops and asks."""
