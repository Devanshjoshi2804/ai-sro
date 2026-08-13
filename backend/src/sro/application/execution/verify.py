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
                    actual = _text(jsonutil.get(document, pointer))
                    if actual != expected:
                        failures.append(f"{pointer} is {actual!r}, expected {expected!r}")

            case AssertionKind.UI_TEXT_VISIBLE:
                # Nothing at this rung is looking at a screen. Recorded as
                # unchecked rather than passed: a UI assertion silently counted
                # as satisfied is how a network replay convinces itself it
                # produced a result nobody saw.
                failures.append(f"cannot check UI text {expected!r} from a network replay")

    return tuple(failures)


def extract(response: HttpResponse, pointer: str) -> str | None:
    """A derived parameter's value from this response, or ``None`` if absent."""
    document = _parse(response.text)
    if not _has(document, pointer):
        return None
    return _text(jsonutil.get(document, pointer))


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


def _text(value: JsonValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return value if isinstance(value, str) else json.dumps(value)
