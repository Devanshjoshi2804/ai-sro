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

The belt order is the product. A state-grounded verifier scored 86.9% against
78.8% for one reading screenshots, with human agreement at 94%, and most
completions leave their proof off-screen -- artifact verification was 192 of 321
tasks. So: the response the command itself returned first, a confirming read the
cited evidence shows the page performs second, and the screenshot last and
least. A green toast is the weakest of the three and the easiest to be wrong
about, and `state_verified` -- which is what a job's earned autonomy counts --
never counts it.
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
    confirming_read,
    expected_statuses,
    mentions,
    status_of,
)
from sro.domain.execution.evidence import writes
from sro.domain.execution.planning import Look
from sro.domain.observation.gesture import Gesture
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
            if status in wanted or (not wanted and 200 <= status < 300):
                return StepVerdict("held", "status", f"the call returned {status}")

    # 2. Hidden state: a read the cited evidence shows this page performs.
    probe = confirming_read(step, by_id)
    # No values means no proposition the read could confirm: a body matches
    # nothing, and "nothing was found" is not evidence the step failed.
    # A probe whose url carries a struck-out credential would ask with the
    # marker's text in the query string; that answers nothing about the state.
    if probe is not None and values and REDACTED not in probe.url:
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
        # The read has to have come back 2xx before its body means anything. A
        # 404 or a 503 answers ok=True with a body that matches nothing, and
        # deciding off `ok` alone marked a correct write failed.
        read_status = status_of(got.result) if got.ok else None
        if read_status is not None and 200 <= read_status < 300:
            if mentions(str(got.result.get("body") or ""), values):
                return StepVerdict(
                    "held", "read", f"a read of {probe.url} shows the value this run supplied"
                )
            return StepVerdict(
                "failed", "read", f"a read of {probe.url} does not show the value this run supplied"
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
