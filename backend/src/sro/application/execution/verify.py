"""Check what the system answered against what the demonstration established.

Every failure is a sentence, because a run's value is what it tells the person
reading it afterwards. "assertion 2 failed" tells them nothing.

Two verifiers live here, for two kinds of step. `check` and its siblings are the
authored skill's post-conditions: assertions somebody wrote down, checked
against one response. `verify` is A14's, for a mined workflow, where nobody
wrote anything down and the only post-condition is "did the thing happen" --
ported from `new_agent_arch/src/rig/verify.py`. The pure half of that one, the
belts that need no wire and no model, is `sro.domain.execution.belts`; this is
the half that sends a probe and asks a model to look at a picture.

The belt order is the product. Measured over the 643 tasks of the WebVoyager
benchmark, a validator reading the run's own text -- what the calls returned --
scored 84.24% against 70.04% for one reading screenshots, with over 84%
agreement with human annotators; a screenshot read beside the agent's final
answer still only reached 83.00%. So: the response the command itself returned
first, a confirming read the cited evidence shows the page performs second, and
the screenshot last and least.

A green toast is the weakest of the three and the
easiest to be wrong about, and `state_verified` -- which is what a job's earned
autonomy counts -- never counts it.

Corrected twice, which is the point of writing it down. What stood here first
-- "86.9% against 78.8%, human agreement at 94%, artifact verification 192 of
321 tasks" -- appears in no version of that paper and nowhere else that could
be found. The correction on 2026-09-14 then said "measured on 322 WebVoyager
tasks", which is also wrong: 322 is the even-`task_id` subset used for the
SELF-VALIDATION experiment in Tables 3 and 4, while Tables 1 and 2 -- the
84.24/70.04/83.00 figures above -- are over the benchmark's 643 tasks. A
replaced number is not a checked number, and the note claiming it had been
checked made the second error harder to see than the first.

Source: *Multimodal Auto Validation for Self-Refinement in Web Agents*,
arXiv:2410.00689, Tables 1 and 2, read from the paper.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from sro.application.capture.rig_wire import headers_without_markers
from sro.application.induction import jsonutil
from sro.application.induction.jsonutil import JsonValue
from sro.application.ports.channel import Channel, Reply
from sro.application.ports.http import HttpResponse
from sro.application.ports.model import Asker
from sro.domain.execution.belts import (
    SCREEN_INSTRUCTIONS,
    SCREEN_SCHEMA,
    StepVerdict,
    carries_every,
    confirming_read,
    expected_statuses,
    mentions,
    status_of,
)
from sro.domain.execution.evidence import recorded_call, writes
from sro.domain.execution.planning import Look
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.shared.hosts import REDACTED
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.workflow import Step


def _was_watched(gesture: Gesture) -> bool:
    """Whether the recorder saw this gesture's traffic complete.

    A call with no status never returned, so it is not evidence of what the
    gesture did -- the same completion guard `origin_of` and `expected_statuses`
    already wear."""
    return any(
        request.status is not None and not request.failure_reason for request in gesture.requests
    )


_PUTS_A_VALUE = frozenset({"type", "select", "upload"})
"""The gesture kinds that put something somewhere. A step citing one of these
is a step that can be wrong in a way nothing else on this page would show --
the right control, the wrong text -- so it is never held on the strength of
"the browser did something"."""


def check(
    assertions: tuple[Assertion, ...],
    response: HttpResponse,
    *,
    values: dict[str, str],
) -> tuple[str, ...]:
    """Failures, in order. Empty means the step satisfied its post-conditions."""
    document: JsonValue = _parse(response.text)
    failures: list[str] = []

    for assertion in assertions:
        expected = assertion.expected.render(values)

        match assertion.kind:
            case AssertionKind.HTTP_STATUS:
                if str(response.status_code) != expected:
                    failures.append(f"expected status {expected}, got {response.status_code}")

            case AssertionKind.RESPONSE_FIELD_PRESENT:
                if not _has(document, assertion.pointer or ""):
                    failures.append(f"response has no {assertion.pointer}")

            case AssertionKind.RESPONSE_FIELD_EQUALS:
                pointer = assertion.pointer or ""
                if not _has(document, pointer):
                    failures.append(f"response has no {pointer}, expected {expected!r}")
                else:
                    actual = jsonutil.as_text(jsonutil.get(document, pointer))
                    if actual != expected:
                        failures.append(f"{pointer} is {actual!r}, expected {expected!r}")

            case AssertionKind.UI_TEXT_VISIBLE:
                # Nothing at this rung is looking at a screen. Recorded as
                # unchecked rather than passed: a UI assertion silently counted
                # as satisfied is how a network replay convinces itself it
                # produced a result nobody saw.
                failures.append(f"cannot check UI text {expected!r} from a network replay")

    return tuple(failures)


def check_text(
    assertions: tuple[Assertion, ...], text: str, *, values: dict[str, str]
) -> tuple[str, ...]:
    """The same post-conditions against a body with no status code behind it.

    What a connector answers is a document, not an HTTP exchange, so the two
    assertions that read a document are checked and the two that read something
    else are reported as unmet rather than skipped. A `http_status` assertion
    on a tool step is a mistake in the mapping, and a mistake nothing mentions
    is a step that verified less than whoever wrote it believed.
    """
    document: JsonValue = _parse(text)
    failures: list[str] = []

    for assertion in assertions:
        expected = assertion.expected.render(values)
        pointer = assertion.pointer or ""

        match assertion.kind:
            case AssertionKind.RESPONSE_FIELD_PRESENT:
                if not _has(document, pointer):
                    failures.append(f"the answer has no {pointer}")

            case AssertionKind.RESPONSE_FIELD_EQUALS:
                if not _has(document, pointer):
                    failures.append(f"the answer has no {pointer}, expected {expected!r}")
                elif (actual := jsonutil.as_text(jsonutil.get(document, pointer))) != expected:
                    failures.append(f"{pointer} is {actual!r}, expected {expected!r}")

            case _:
                failures.append(
                    f"a {assertion.kind.value} assertion cannot be checked against a tool's "
                    "answer, which has no status code and no screen"
                )

    return tuple(failures)


def check_on_screen(
    assertions: tuple[Assertion, ...], text_digest: str, *, values: dict[str, str]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The same post-conditions, against a screen instead of a response.

    A gesture landing is not a task being done. The driver answers "performed"
    when it found a control and clicked it, and for a run in the interface that
    was the whole of the verification: a click on the wrong Save, or the right
    Save on a form the application refused, was recorded as a step that
    succeeded and counted towards the version's promotion. Verification is
    supposed to be the control that stands between a model and a warehouse.

    Returns failures and, separately, what could not be checked at this rung --
    a response body is not visible from here, and the honest thing is to say so
    rather than to count it as satisfied or to fail a run over it. The
    demonstration's own evidence is what is checked: the text that appeared on
    screen in both runs after this gesture.
    """
    failures: list[str] = []
    unchecked: list[str] = []
    shown = text_digest.lower()

    for assertion in assertions:
        expected = assertion.expected.render(values)
        if assertion.kind is AssertionKind.UI_TEXT_VISIBLE:
            if expected.lower() not in shown:
                failures.append(f"the screen does not show {expected!r}")
            continue
        unchecked.append(str(assertion.kind.value))

    return tuple(failures), tuple(dict.fromkeys(unchecked))


def extract(response: HttpResponse, pointer: str) -> str | None:
    """A derived parameter's value from this response, or ``None`` if absent."""
    document = _parse(response.text)
    if not _has(document, pointer):
        return None
    return jsonutil.as_text(jsonutil.get(document, pointer))


def _parse(text: str) -> JsonValue:
    try:
        return json.loads(text)
    except ValueError:
        return None


def _has(document: JsonValue, pointer: str) -> bool:
    if document is None:
        return False
    try:
        jsonutil.get(document, pointer)
    except (KeyError, IndexError, TypeError, ValueError):
        return False
    return True


async def already_done(
    *,
    step: Step,
    cited: list[Gesture],
    values: Mapping[str, str],
    channel: Channel,
    tenant_id: TenantId,
    device_id: DeviceId,
    run_id: str,
) -> str | None:
    """Whether this write's effect is already true, said in a sentence.

    The verifier's second rung, asked BEFORE the write instead of after. It is
    the same question in both places -- does the system already show the value
    this run would supply -- and the answer means something different on each
    side of the send: after, the write worked; before, there is nothing to do.

    The run that made this worth writing signed an operator in who was already
    signed in, and there is a whole class behind it: a rule fires twice, two
    browsers fire the same job, somebody presses Yes on a card they pressed
    yesterday. Every one of those is a second record in a warehouse that wanted
    one, and no amount of care in the runner can take a duplicate back.

    Narrow in the same three ways the after-the-fact rung is narrow: only a
    step whose evidence shows the page performing a read after its write, only
    when this run actually carries values for the read to show, and only when
    the read comes back 2xx -- a 404 or a 503 says nothing about the state and
    must never be read as "already there", which would skip a write that never
    happened.

    Returns the sentence to record, or None to go ahead and do the step. None
    is the safe answer and the common one: a step with no probe, a read that
    could not be made, a body that does not carry the value.
    """
    by_id = {gesture.id: gesture for gesture in cited}
    probe = confirming_read(step, by_id)
    if probe is None or not values or REDACTED in probe.url:
        return None
    # Only values that say WHICH record. A run carries its context as well as
    # its content -- a facility, a site, a warehouse -- and those appear in the
    # probe's own url because they are what the page is scoped to. They also
    # appear in every row it returns, so a list read would match on them and
    # skip a write for a record nobody has created yet. Asked after the write
    # this does not matter; asked before it, it is the difference between
    # "already there" and "this is the right screen".
    distinctive = {
        name: value for name, value in values.items() if value and value not in probe.url
    }
    if not distinctive:
        return None
    got = await _read_back(probe, channel, tenant_id, device_id, run_id)
    # EVERY distinctive value, not any of them. A job carries values that
    # change from run to run beside values that do not, and `mentions` -- the
    # right rule after the write, where one value coming back is the record
    # coming back -- reads a record whose unchanged half matches as the record
    # this run was about to create. Four live runs of a three-step job proved
    # it on 2026-09-15: a new client code each time, the same reference, and
    # all four skipped the write on the PREVIOUS record's reference and
    # reported `held` with nothing sent.
    if got is None or not carries_every(got, distinctive):
        return None
    return (
        f"a read of {probe.url} already shows the value this run would supply, "
        "so the step was not performed again"
    )


async def _read_back(
    probe: Call,
    channel: Channel,
    tenant_id: TenantId,
    device_id: DeviceId,
    run_id: str,
) -> str | None:
    """The confirming read, made, or None where it answers nothing.

    One function for the two callers -- the rung that judges a write and the
    precondition that decides whether to make one -- because a read that counts
    as evidence in one of them and not in the other is two rules for one fact.
    """
    got = await channel.send(
        tenant_id,
        device_id,
        kind="http.send",
        run_id=run_id,
        payload={
            "method": "GET",
            "url": probe.url,
            "headers": headers_without_markers(probe.request_headers),
            "body": None,
        },
    )
    # The read has to have come back 2xx before its body means anything. A 404
    # or a 503 answers ok=True with a body that matches nothing.
    status = status_of(got.result) if got.ok else None
    if status is None or not (200 <= status < 300):
        return None
    return str(got.result.get("body") or "")


async def by_what_the_page_called(
    *,
    step: Step,
    cited: list[Gesture],
    since: float,
    channel: Channel,
    tenant_id: TenantId,
    device_id: DeviceId,
    run_id: str,
) -> StepVerdict | None:
    """The status the warehouse answered this step with, or None to look.

    Rung 1 of the ladder, for a step performed in a browser rather than
    replayed over http. The verifier's own docstring puts the response the
    command returned first and the screenshot last and least -- and until this
    existed, a UI step could never reach the first rung, because a click's
    reply says "I found the control and clicked it" and nothing about what the
    server said. So every step of every run this deployment has performed was
    judged by photographing the screen and asking a model: `verdict_by =
    screen`, 67 times out of 67, the slowest and weakest rung there is.

    The browser keeps the calls its own driven tab made for the length of the
    run -- out of the evidence plane, which still drops them, and in a bounded
    map it can be asked about. This asks, and decides only when the step's own
    demonstrated endpoint is among them:

    **Only a step whose evidence recorded a write.** A step that changes
    nothing has no status to be held by, and 2xx on a page's keep-alive is not
    a step being done.

    **Only that endpoint.** Matched by method and path shape, so an id in the
    path is not a mismatch and a telemetry beacon on the same host is not a
    match. This is `expected_statuses`' rule, which the same beacons taught it.

    **None means look.** No call, no status, or an endpoint nobody recognises
    is not evidence the step failed -- it is the absence of evidence, and the
    ladder goes on to the read and the screen.
    """
    by_id = {gesture.id: gesture for gesture in cited}
    replayed = recorded_call(step, by_id)
    if replayed is None or not writes(step, by_id):
        return None

    # `since` is sent and the browser does not compare against it. It cannot:
    # this is the server's clock and the calls are the browser's, and while
    # that comparison stood -- an ISO string against a float -- it was false
    # for every call ever made and this rung never once fired. The extension
    # marks its own counter when a command goes out and answers with what came
    # after it (`commands.js`'s `marks`), which has one clock and no skew. The
    # value stays on the wire because it is what an older extension reads.
    got = await channel.send(
        tenant_id, device_id, kind="calls.since", run_id=run_id, payload={"since": since}
    )
    if not got.ok:
        return None

    wanted = expected_statuses(step, by_id)
    method, shape = replayed.method.upper(), path_shape(replayed.url)
    made = got.result.get("calls") if isinstance(got.result, dict) else None
    for call in reversed(made if isinstance(made, list) else []):
        if not isinstance(call, dict):
            continue
        status = call.get("status")
        if not isinstance(status, int):
            continue
        if str(call.get("method", "")).upper() != method:
            continue
        if path_shape(str(call.get("url", ""))) != shape:
            continue
        if status >= 400:
            return StepVerdict("failed", "status", f"{method} {shape} returned {status}")
        if status in wanted or (not wanted and 200 <= status < 300):
            return StepVerdict(
                "held",
                "status",
                f"{method} {shape} returned {status}",
                made=made_by(call),
            )
        # The endpoint answered something the demonstration never saw. Not a
        # failure and not a hold: exactly the case the rest of the ladder is
        # for.
        return None
    return None


K_IDENTIFIES = ("id", "code", "name", "number", "key")
"""Which fields of a create's answer say WHICH record it made.

Read by suffix and case-insensitively, because a warehouse names them its own
way: `equipmentTypeId`, `workAreaCode`, `supplierNumber`. Nothing else of the
body is kept -- a created record's answer is a row of somebody's data, and what
a person needs in order to go and look at it is what it is called."""

K_NAMED = 6
"""How many of those fields are kept. A record is identified by one or two of
them; a body with a dozen matching names is a list, not a record."""


def made_by(call: Mapping[str, object]) -> dict[str, str]:
    """What the warehouse called the record this create made.

    A run that made three records has to be able to say which three, or nobody
    can go and look at them -- and an undo, the day the evidence for one
    exists, has to address them by whatever the system called them.

    Never the whole body. A create's answer is a row of a customer's data, and
    this is stored on the run for as long as the tenant keeps it: what is kept
    is the handful of fields that NAME the row, and only where their values are
    short enough to be an identifier rather than a paragraph.
    """
    text = call.get("body")
    if not isinstance(text, str) or not text.strip():
        return {}
    try:
        parsed = json.loads(text)
    except ValueError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    # The envelope, before the record. Blue Yonder answers a create with
    # `{"@type": "ResponseBodyWrapper", "data": {…}}` -- 112 of the 114
    # successful writes in `knowledge-base/http/exchanges/*.jsonl`, and the live
    # deployment's own create of `GGD` is one of them. Read at the top level
    # that is `@type`, which names nothing, and `data`, which is a dict and
    # skipped: every real create would have said it made nothing at all.
    #
    # A `data` holding a LIST is left alone. That is `waves.jsonl`, the two
    # exceptions, and a list is not a record for the same reason `K_NAMED`
    # stops at a handful -- a body with a dozen identifying names is a
    # collection, and naming it as one row would be a lie on the run.
    inner = parsed.get("data")
    if isinstance(inner, dict):
        parsed = inner
    named: dict[str, str] = {}
    for key, value in parsed.items():
        if not isinstance(key, str) or not isinstance(value, str | int):
            continue
        if not key.lower().endswith(K_IDENTIFIES):
            continue
        said = str(value).strip()
        if said and len(said) <= 64:
            named[key] = said
        if len(named) == K_NAMED:
            break
    return named


async def verify(
    *,
    step: Step,
    sent_kind: str,
    answer: Reply,
    cited: list[Gesture],
    values: Mapping[str, str],
    look_before: Look,
    look_after: Look,
    channel: Channel,
    tenant_id: TenantId,
    device_id: DeviceId,
    run_id: str,
    # Unused, and kept: the extension picks the probe's tab from the url itself
    # (tabOnOrigin), so an origin in the payload would be ignored. The parameter
    # is here because the runner calls every step's verifier the same way --
    # `test_the_probe_names_no_origin_because_the_url_already_does` fails if a
    # probe ever starts carrying one.
    origin: str | None,
    asker: Asker,
    model: str,
    rewrote: bool = False,
) -> StepVerdict:
    """Did this step actually happen: state first, and a picture only last."""
    if not answer.ok:
        return StepVerdict("failed", "none", answer.detail)
    by_id = {gesture.id: gesture for gesture in cited}

    # 1. Artifact: what the command itself returned.
    if sent_kind == "http.send":
        status = status_of(answer.result)
        if status is not None:
            # Refusal first: a demonstration that recorded a 409 would otherwise
            # teach the verifier that a 409 is what success looks like. What the
            # operator got is evidence, not a licence.
            if status >= 400:
                return StepVerdict("failed", "status", f"the call returned {status}")
            wanted = expected_statuses(step, by_id)
            # Belt ORDER, not belt availability -- but only for bytes sent as
            # they were recorded. `test_a_status_that_already_decided_is_not_
            # second_guessed_by_a_read` is the rule, and it holds because the
            # endpoint answered the demonstration the same way, so its answer
            # means the demonstrated effect.
            #
            # A body this run RE-AIMED breaks that. The status then says
            # something was created; it does not say the thing carries the
            # values this run was given. The ledger's own note is the instance
            # -- `csttyp truncates at 4 chars`, so a create asking for five
            # characters is answered 201 and the record is four, with nobody
            # told. So a re-aimed write falls through to the read-back below,
            # which is the belt that can tell.
            if not rewrote and (status in wanted or (not wanted and 200 <= status < 300)):
                return StepVerdict(
                    "held",
                    "status",
                    f"the call returned {status}",
                    made=made_by(answer.result),
                )

    # 2. Hidden state: a read the cited evidence shows this page performs.
    probe = confirming_read(step, by_id)
    # No values means no proposition the read could confirm: a body matches
    # nothing, and "nothing was found" is not evidence the step failed.
    # A probe whose url carries a struck-out credential would ask with the
    # marker's text in the query string; that answers nothing about the state.
    if probe is not None and values and REDACTED not in probe.url:
        body = await _read_back(probe, channel, tenant_id, device_id, run_id)
        if body is not None:
            # `carries_every` for a body this run re-aimed, `mentions` for the
            # rest, and the difference is the whole point of reaching here at
            # all. `mentions` is `any`, so a record whose UNCHANGED half matches
            # reads as the record this run meant to create -- which is exactly
            # what a truncated code looks like: the description still matches
            # and the code does not. Measured live on 2026-09-15, four runs of
            # a job that types a new code and the same reference each time all
            # skipped their write and reported held on `any`.
            shown = carries_every(body, values) if rewrote else mentions(body, values)
            if shown:
                return StepVerdict(
                    "held", "read", f"a read of {probe.url} shows the value this run supplied"
                )
            return StepVerdict(
                "failed", "read", f"a read of {probe.url} does not show the value this run supplied"
            )
    if rewrote:
        # Belt AVAILABILITY, and this is where it is decided rather than
        # assumed. A re-aimed write whose evidence carries no confirming read --
        # or a run with no values for one to confirm -- has nothing but its
        # status, and the status is real. Falling to the screen for it would
        # photograph a page to ask a model about a record the warehouse already
        # answered for.
        status = status_of(answer.result)
        if status is not None and 200 <= status < 300:
            return StepVerdict(
                "held",
                "status",
                f"the call returned {status}, and this job records no read to confirm it by",
                made=made_by(answer.result),
            )

    # 3. Visible state: last, and least.
    if look_after.screenshot is None:
        # Nothing to see, and for some steps nothing to have seen. A step whose
        # own evidence carries no write and no typing changed nothing: it
        # opened a mail, moved to a tab, followed a link. There is no state for
        # rungs 1 and 2 to confirm and no proposition a picture could settle,
        # so "I cannot tell" is the wrong answer -- the browser reporting that
        # it performed the command and found the control is the whole of the
        # evidence such a step can ever have.
        #
        # This matters because `run_workflow` stops on anything but `held`, and
        # rightly: a step nobody watched succeed is one the rest of the job
        # assumes. But every cross-system job this rig mines BEGINS with a step
        # like this -- `new`'s `Create a Warehouse Equipment Type` opens the
        # request in Gmail before it touches the WMS -- so an `unclear` here
        # stopped the job on its first rung, every time, whatever came after.
        #
        # Last, and only with no screenshot, on purpose. Where a browser
        # supplies one the model still looks, and a click that missed is caught
        # there. This does not spend that check to save a model call; it
        # answers the case where the check cannot run at all.
        #
        # "Changes nothing" and "we have no evidence either way" are not the
        # same claim, and only the first earns a `held`. A step whose cited
        # gestures recorded no completed traffic at all -- the capture missed
        # it, or a re-mine took the evidence with it -- is the second, and it
        # stays `unclear`. What this rung asserts is that the traffic WAS
        # watched and none of it on the page's own origin mutated anything.
        if (
            not writes(step, by_id)
            and any(_was_watched(gesture) for gesture in cited)
            and not any(gesture.action.kind in _PUTS_A_VALUE for gesture in cited)
        ):
            return StepVerdict(
                "held",
                "performed",
                "this step changes nothing, and the browser performed it",
            )
        return StepVerdict(
            "unclear",
            "none",
            "nothing returned a status, nothing to read, and no screen to look at",
        )
    evidence = json.dumps(
        {
            "step": {"says": step.says},
            "sent": sent_kind,
            # Not `answer.result` whole: for an http.send that is the response
            # body and headers, and nothing here trims them. The model is
            # judging a picture; it does not need the payload to do it.
            "browser_answered": {"ok": answer.ok, "status": status_of(answer.result)},
            "screen_before": look_before.digest,
            "screen_after": look_after.digest,
            "values": dict(values),
        },
        indent=2,
        # The redaction marker is «redacted»; the default ensure_ascii would
        # write it into the prompt in a form nothing else in this system uses.
        ensure_ascii=False,
    )
    judged = await asker.ask(
        model=model,
        instructions=SCREEN_INSTRUCTIONS,
        evidence=evidence,
        schema=SCREEN_SCHEMA,
        image=look_after.screenshot,
    )
    if judged.data is None:
        return StepVerdict(
            "unclear", "screen", judged.error or "the model returned nothing", judged
        )
    held = bool(judged.data.get("held"))
    return StepVerdict(
        "held" if held else "failed", "screen", str(judged.data.get("why") or ""), judged
    )
