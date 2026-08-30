"""Check what the system answered against what the demonstration established.

Every failure is a sentence, because a run's value is what it tells the person
reading it afterwards. "assertion 2 failed" tells them nothing.
"""

from __future__ import annotations

import json

from sro.application.induction import jsonutil
from sro.application.induction.jsonutil import JsonValue
from sro.application.ports.http import HttpResponse
from sro.domain.skill.assertion import Assertion, AssertionKind


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
