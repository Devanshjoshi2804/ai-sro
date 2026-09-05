"""A14: verify against state, and only then against a picture.

A state-grounded verifier scored 86.9% against 78.8% for one reading
screenshots, with human agreement at 94%. Most completions leave their proof
off-screen -- artifact verification was 192 of 321 tasks. So: the response the
command itself returned first, a confirming read the cited evidence shows the
page performs second, and the screenshot last and least. A green toast is the
weakest of the three and the easiest to be wrong about.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from rig.channel import Answer as Reply
from rig.channel import Channel
from rig.locators import recorded_call
from rig.models import Answer, Asker
from rig.planner import Look
from rig.records import Gesture
from rig.wire import REDACTED, Request
from rig.workflows import Step

VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    # held first, why last: decide, then explain.
    "properties": {"held": {"type": "boolean"}, "why": {"type": "string"}},
    "required": ["held", "why"],
    "propertyOrdering": ["held", "why"],
}

INSTRUCTIONS = """You are checking whether one step of a warehouse job was actually done.
You are shown the step, what was sent, what the browser answered, the screen
text before and after, and the screen after. Answer whether the step HELD --
whether the thing it was meant to do is now true on the screen -- and say why
in one sentence. Do not assume success from the absence of an error."""


@dataclass(frozen=True, slots=True)
class Verdict:
    state: str  # held | failed | unclear
    by: str  # status | read | screen | none
    reason: str
    answer: Answer | None = None


def expected_statuses(step: Step, by_id: Mapping[str, Gesture]) -> set[int]:
    """Every status the cited evidence's mutation actually came back with.

    A request with a `failure_reason` never completed, so whatever status it
    carries is not a status the warehouse returned -- see `origin_of`, which
    learned the same thing about picking a host off a dead call.
    """
    found: set[int] = set()
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for request in gesture.requests:
            if request.method.upper() in ("GET", "HEAD", "OPTIONS"):
                continue
            if request.status is not None and not request.failure_reason:
                found.add(request.status)
    return found


def confirming_read(step: Step, by_id: Mapping[str, Gesture]) -> Request | None:
    """A GET a cited gesture made after its write: the read the page performs
    to show the result, which is the hidden state a run can ask for again."""
    call = recorded_call(step, by_id)
    if call is None or call.method.upper() in ("GET", "HEAD", "OPTIONS"):
        return None
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for request in gesture.requests:
            if request.method.upper() == "GET" and request.started_at > call.started_at:
                return request
    return None


def _mentions(body: str, values: Mapping[str, str]) -> bool:
    return any(value and value in body for value in values.values())


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
    device_id: str,
    run_id: str,
    origin: str | None,
    asker: Asker,
    model: str,
) -> Verdict:
    if not answer.ok:
        return Verdict("failed", "none", answer.detail)
    by_id = {g.id: g for g in cited}

    # 1. Artifact: what the command itself returned.
    if sent_kind == "http.send":
        status = answer.result.get("status")
        if isinstance(status, int):
            wanted = expected_statuses(step, by_id)
            if status in wanted or (not wanted and 200 <= status < 300):
                return Verdict("held", "status", f"the call returned {status}")
            if status >= 400:
                return Verdict("failed", "status", f"the call returned {status}")

    # 2. Hidden state: a read the cited evidence shows this page performs.
    probe = confirming_read(step, by_id)
    if probe is not None and values:
        got = await channel.send(
            device_id,
            kind="http.send",
            run_id=run_id,
            payload={
                "method": "GET",
                "url": probe.url,
                # Never a header whose stored value is the redaction marker:
                # the same rule the planner applies to a replayed call.
                "headers": {k: v for k, v in probe.request_headers.items() if REDACTED not in v},
                "body": None,
            },
        )
        body = str(got.result.get("body") or "") if got.ok else ""
        if got.ok and _mentions(body, values):
            return Verdict(
                "held", "read", f"a read of {probe.url} shows the value this run supplied"
            )
        if got.ok:
            return Verdict(
                "failed", "read", f"a read of {probe.url} does not show the value this run supplied"
            )

    # 3. Visible state: last, and least.
    if look_after.screenshot is None:
        return Verdict(
            "unclear",
            "none",
            "nothing returned a status, nothing to read, and no screen to look at",
        )
    evidence = json.dumps(
        {
            "step": {"says": step.says},
            "sent": sent_kind,
            "browser_answered": answer.result,
            "screen_before": look_before.digest,
            "screen_after": look_after.digest,
            "values": dict(values),
        },
        indent=2,
        ensure_ascii=False,
    )
    judged = await asker.ask(
        model=model,
        instructions=INSTRUCTIONS,
        evidence=evidence,
        schema=VERDICT_SCHEMA,
        image=look_after.screenshot,
    )
    if judged.data is None:
        return Verdict("unclear", "screen", judged.error or "the model returned nothing", judged)
    held = bool(judged.data.get("held"))
    return Verdict(
        "held" if held else "failed", "screen", str(judged.data.get("why") or ""), judged
    )
