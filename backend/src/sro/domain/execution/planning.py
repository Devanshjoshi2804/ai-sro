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
    {"ui.perform_at", "ui.url", "screenshot", "abort", "tab.open", "calls.since", "sign_in"}
)
"""Everything the runner may put on the wire, plan or not.

`KINDS` is the subset a model may choose; the rest the runner sends on its own
-- the sight rung's point (`ui.perform_at`), the two the run asks a browser for
before and after a step (`ui.url`, `screenshot`), the one it asks for the
calls the page made while it was being driven (`calls.since`, which is how a
step performed in a browser can reach the verifier's first rung at all), the
one it sends when a run
is stopped (`abort`), the one a LOOKUP sends when the system it has to
read is one nobody has open (`tab.open`), and the one a run sends when the page
in front of it turns out to be a login (`sign_in`). Deliberately not in
`KINDS`: opening a tab is never a step of a job, it is what has to be true
before a read can happen at all -- and signing in is never a step of a job
either. A model that could CHOOSE to sign in would be a model that can decide
to put a credential on a page, and what decides that here is a page with a
password box on it and a vault with something in it.

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
    refused: str = ""
    """Why there is no picture, in the browser's own words.

    A rung that cannot see says "no screen to look at", and until this that was
    the whole of what a run recorded about it -- measured on the deployment,
    2026-09-17 at 15:20, where two runs in a row gave up on the same step with
    that sentence and nothing anywhere said whether the tab was refused, was
    not the visible one, or answered with a picture of zero size. Three
    different faults with three different fixes, told apart by nothing.

    Empty where a picture arrived, and where there was never one asked for."""

    elsewhere: str = ""
    """Where the browser actually is, when it is not on the origin at all.

    A step reads the tab on the system it names, which is right for driving
    and blinding for reading: an interruption is on ANOTHER origin by
    definition -- a sign-in bounced to the platform's login host, a consent
    screen, an error page a proxy served. The browser then answered nothing,
    the look had no url, and the run said *the browser is on None* while the
    person watched a sign-in page. Measured on the deployment 2026-09-19, run
    `run_fdc7e7ff`.

    So the browser now answers with the page in front of the person when it
    cannot answer with the one the step wanted. `url` stays empty -- the step
    has NOT arrived and nothing may read it as arrived -- and this says where
    it went instead, which is what every sentence below needs to be legible.

    Empty when the browser is where the step expected it, and when there was
    no tab at all to ask about."""

    elsewhere_is_ours: bool = False
    """Whether `elsewhere` is THIS RUN's own tab, or a guess.

    The browser answers with the run's pinned tab where it has one -- the page
    this job navigated to, and the page it is about to be driven in -- and
    otherwise with whatever tab is in front, which is the operator's other
    window, a mailbox, a search. Both are worth REPORTING and only the first
    is worth ACTING on, and nothing could tell them apart.

    What that cost, measured on the deployment 2026-09-20, run
    `run_b949148d`: `Log in using Azure B2C SSO` is a job whose every gesture
    is on `blueyonderalphaus.b2clogin.com`. The live sign-in bounced to
    Keycloak instead, and the run -- unable to read where it was -- fell back
    to the origin its RECORDING named, asked for the b2clogin password, and
    typed it into the Keycloak form. The page said *Invalid username or
    password*. A credential in the wrong system's box is worse than a step
    that fails: it spends an account's lockout budget."""

    signed_out: bool = False
    """The page in front of the browser is asking somebody to sign in.

    A dead session is the commonest reason a run cannot find anything, and it
    arrived as `control_not_found` -- no control matched, which is true and
    says nothing about why. Somebody reading that goes looking for a broken
    selector. Measured on the deployment 2026-09-18: a session expired, the
    operator spent minutes signing back in, and every run in between blamed a
    missing tab item.

    A password field on the page and nothing else, which is the rule
    `check_session` keeps server-side and keeps for the reason that matters --
    any heuristic on WORDS fires on a warehouse screen that mentions a
    password, and a run that stopped saying "you are signed out" in front of a
    working screen would be worse than one that says nothing.

    False wherever nothing could be asked. This is a reason to stop and it must
    never be a reason invented by a failure to look."""

    dialog: str = ""
    """What a dialog over the page says, where there is one.

    The other half of the same question, and the case this deployment's own
    ledger already names: `Existing Carriers duplicate check is SERVER-side:
    the form accepts the click and only then shows an in-app 'Record already
    exists' modal.` A step that clicked Save and then found nothing is a step
    whose answer is on the screen, in a box, in words -- and the run reported a
    missing control.

    The dialog is found by STRUCTURE, like the login: a `<dialog open>`, a
    `role="dialog"`, or the one class name the framework these systems are
    built with uses. What is carried back is its TEXT, which is not a heuristic
    -- it is the evidence, and it is the whole answer to why the step did
    nothing."""

    loading: bool = False
    """The page has not finished arriving.

    The one of these a run can do something about other than stop. What a
    half-drawn screen needs is a moment, and every rung of the ladder spent on
    one is a model call answering a question about a page that was not there
    yet -- then a `sight` rung photographing a spinner, and a step reporting a
    missing control that appeared a second after it gave up.

    `document.readyState`, and a visible progress bar or panel mask for the
    case it cannot answer: a single-page application finished its document
    minutes ago and is now fetching the screen, and `readyState` has said
    `complete` the whole time."""


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
        # WHAT the point is, which is required and so cannot be skipped.
        #
        # This was an optional `open_first` object, and it was skipped every
        # time: the model wrote "it is likely under the 'Partners' menu" in
        # `why` and left the field null, twice in a row, with the Partners tab
        # plainly on the screen it was looking at. A model fills what a schema
        # demands and passes over what it offers.
        #
        # So there is one point and one question about it. `the_control` is
        # the step itself; `what_reveals_it` is a menu to open first, clicked
        # instead of the step, after which this rung is asked again with a new
        # picture; `nothing` is nowhere to point, which is the honest refusal
        # this rung must always be able to give.
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
