from __future__ import annotations

import json
from collections.abc import Mapping
from types import MappingProxyType

from sro.application.capture.rig_wire import headers_without_markers
from sro.application.induction import jsonutil
from sro.application.induction.jsonutil import JsonValue
from sro.application.ports.channel import Channel, Reply
from sro.application.ports.http import HttpResponse
from sro.application.ports.model import Asker
from sro.application.shared.asking import ask
from sro.domain.execution.belts import (
    StepVerdict,
    carries_every,
    confirming_read,
    expected_statuses,
    mentions,
    record_carrying,
    status_of,
    unreturned,
)
from sro.domain.execution.evidence import primary_gesture, recorded_call, writes
from sro.domain.execution.planning import Look
from sro.domain.execution.records import made_by
from sro.domain.execution.secrets import needs_a_secret
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.prompts.check_step import CHECK_SCREEN, CHECK_WAY_THROUGH
from sro.domain.shared.hosts import REDACTED
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.workflow import Step


def _was_watched(gesture: Gesture) -> bool:
    return any(
        request.status is not None and not request.failure_reason for request in gesture.requests
    )


_PUTS_A_VALUE = frozenset({"type", "select", "upload"})


def check(
    assertions: tuple[Assertion, ...],
    response: HttpResponse,
    *,
    values: dict[str, str],
) -> tuple[str, ...]:
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
                failures.append(f"cannot check UI text {expected!r} from a network replay")

    return tuple(failures)


def check_text(
    assertions: tuple[Assertion, ...], text: str, *, values: dict[str, str]
) -> tuple[str, ...]:
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


K_SCREEN_SAID = 600


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
    by_id = {gesture.id: gesture for gesture in cited}
    probe = confirming_read(step, by_id)
    if probe is None or not values or REDACTED in probe.url:
        return None
    distinctive = {
        name: value for name, value in values.items() if value and value not in probe.url
    }
    if not distinctive:
        return None
    got = await _read_back(probe, channel, tenant_id, device_id, run_id)
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
    aimed_url: str | None = None,
) -> StepVerdict | None:
    by_id = {gesture.id: gesture for gesture in cited}
    replayed = recorded_call(step, by_id)
    if replayed is None or not writes(step, by_id):
        return None

    got = await channel.send(
        tenant_id, device_id, kind="calls.since", run_id=run_id, payload={"since": since}
    )
    if not got.ok:
        return None

    wanted = expected_statuses(step, by_id)
    method, shape = replayed.method.upper(), path_shape(aimed_url or replayed.url)
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
                called={"method": method, "url": str(call.get("url", ""))},
            )
        return None
    return None


def _named(record: Mapping[str, object] | None, wanted: Mapping[str, str]) -> dict[str, str]:
    if record is None:
        return {}
    named: dict[str, str] = {}
    for slot in wanted:
        value = record.get(slot)
        if isinstance(value, str | int) and (said := str(value).strip()) and len(said) <= 64:
            named[slot] = said
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
    origin: str | None,
    asker: Asker,
    rewrote: bool = False,
    confirm: Mapping[str, str] = MappingProxyType({}),
    next_says: str | None = None,
) -> StepVerdict:
    if not answer.ok:
        return StepVerdict("failed", "none", answer.detail)
    by_id = {gesture.id: gesture for gesture in cited}

    if sent_kind == "http.send":
        status = status_of(answer.result)
        if status is not None:
            if status >= 400:
                return StepVerdict("failed", "status", f"the call returned {status}")
            wanted = expected_statuses(step, by_id)
            if not rewrote and (status in wanted or (not wanted and 200 <= status < 300)):
                return StepVerdict(
                    "held",
                    "status",
                    f"the call returned {status}",
                    made=made_by(answer.result),
                )

    probe = confirming_read(step, by_id)
    askable = bool(confirm) if rewrote else bool(values)
    if probe is not None and askable and REDACTED not in probe.url:
        body = await _read_back(probe, channel, tenant_id, device_id, run_id)
        if body is not None:
            found = record_carrying(body, confirm) if rewrote else None
            shown = found is not None if rewrote else mentions(body, values)
            if shown:
                missing_back = unreturned(body, values)
                return StepVerdict(
                    "held",
                    "read",
                    f"a read of {probe.url} shows the value this run supplied"
                    + (
                        f" — and does not show what was sent for {', '.join(missing_back)}"
                        if missing_back
                        else ""
                    ),
                    made=_named(found, confirm),
                )
            return StepVerdict(
                "failed",
                "read",
                f"a read of {probe.url} does not show the value this run supplied",
                refuted=True,
            )
    if rewrote:
        status = status_of(answer.result)
        if status is not None and 200 <= status < 300:
            return StepVerdict(
                "held",
                "status",
                f"the call returned {status}, and this job records no read to confirm it by",
                made=made_by(answer.result),
            )

    changes_nothing = not writes(step, by_id) and not any(
        gesture.action.kind in _PUTS_A_VALUE for gesture in cited
    )
    if look_after.screenshot is None:
        if changes_nothing and any(_was_watched(gesture) for gesture in cited):
            return StepVerdict(
                "held",
                "performed",
                "this step changes nothing, and the browser performed it",
            )
        return StepVerdict(
            "unclear",
            "none",
            "nothing returned a status, nothing to read, and no screen to look at"
            + (f": {look_after.refused}" if look_after.refused else ""),
        )
    evidence = json.dumps(
        {
            "step": {"says": step.says},
            "sent": sent_kind,
            "browser_answered": {"ok": answer.ok, "status": status_of(answer.result)},
            "screen_before": look_before.digest,
            "screen_after": look_after.digest,
            "values": dict(values),
            **({"next_step": next_says} if changes_nothing and next_says else {}),
        },
        indent=2,
        ensure_ascii=False,
    )
    judged = await ask(
        asker,
        CHECK_WAY_THROUGH if changes_nothing else CHECK_SCREEN,
        trusted={},
        untrusted={"evidence": evidence},
        image=look_after.screenshot,
    )
    if judged.data is None:
        return StepVerdict(
            "unclear", "screen", judged.error or "the model returned nothing", judged
        )
    held = bool(judged.data.get("held"))
    why = str(judged.data.get("why") or "")
    aimed = primary_gesture(step, {gesture.id: gesture for gesture in cited})
    if held and aimed is not None and needs_a_secret(aimed):
        return StepVerdict(
            "unclear",
            "screen",
            "a credential field is masked, so the screen cannot say it was typed"
            + (f" — the model read: {why}" if why else ""),
            judged,
        )
    if held:
        return StepVerdict("held", "screen", why, judged)
    said = " ".join(look_after.digest.split())[:K_SCREEN_SAID]
    return StepVerdict(
        "failed",
        "screen",
        f"{why} — the screen said: {said}" if said else why,
        judged,
    )
