from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field

from sro.domain.execution.evidence import READ_METHODS, recorded_call
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step

K_WEAK_LOCATORS = frozenset({"css_path", None})

K_EARNED_RUNS = 3

STATE_BELTS = ("status", "read")

SCREEN_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"held": {"type": "boolean"}, "why": {"type": "string"}},
    "required": ["held", "why"],
    "propertyOrdering": ["held", "why"],
}

SCREEN_INSTRUCTIONS = """You are checking whether one step of a warehouse job was actually done.
You are shown the step, what was sent, what the browser answered, the screen
text before and after, and the screen after. Answer whether the step HELD --
whether the thing it was meant to do is now true on the screen -- and say why
in one sentence. Do not assume success from the absence of an error.

Your sentence must be about the thing the STEP names. Where the step names a
field, a list or a control, say what that one now shows. If it is empty, or
you cannot find it on the screen at all, the step did not hold -- whatever
else on the page looks healthy. A page with no errors on it is not evidence
that this step did anything, and neither is a button further down being
visible."""


WAY_THROUGH_INSTRUCTIONS = """
You are checking one step of a warehouse job that changes nothing by itself.
Its own recording sent no request and put no value anywhere: it opened a menu,
focused a field, moved to a tab. The sentence describing it was written by
another model from the recording, and it may be a guess about what the click
was FOR -- so do not check it.

Check only whether the job can go on. Where you are told `next_step`, that is
the question: could somebody looking at this screen now do that next thing?
Answer held=false if they could not -- an error, a sign-in page, a blank or
half-drawn screen, a dialog or a suggestion list sitting over what they would
have to use, or a screen that has not brought up the thing the next step needs
to act on. Answer held=true otherwise, including when the screen looks exactly
as it did before and the next step can still be done from it. Where there is
no `next_step`, this is the job's last step: answer held=false only if the
screen is showing something that plainly went wrong.

Say why in one sentence."""


@dataclass(frozen=True, slots=True)
class StepVerdict:
    state: str
    by: str
    reason: str
    answer: Answer | None = None

    made: Mapping[str, str] = field(default_factory=dict)

    refuted: bool = False

    called: Mapping[str, str] = field(default_factory=dict)


def expected_statuses(step: Step, by_id: Mapping[str, Gesture]) -> set[int]:
    replayed = recorded_call(step, by_id)
    if replayed is None or replayed.method.upper() in READ_METHODS:
        return set()
    method = replayed.method.upper()
    found: set[int] = set()
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for request in gesture.requests:
            if request.method.upper() != method or request.url != replayed.url:
                continue
            if request.status is not None and not request.failure_reason:
                found.add(request.status)
    return found


def confirming_read(step: Step, by_id: Mapping[str, Gesture]) -> Call | None:
    call = recorded_call(step, by_id)
    if call is None or call.method.upper() in READ_METHODS or call.started_at is None:
        return None
    wrote_at = call.started_at
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for request in gesture.requests:
            if request.method.upper() != "GET":
                continue
            if request.started_at is None or request.started_at <= wrote_at:
                continue
            if request.status is not None and not request.failure_reason:
                return request
    return None


def status_of(result: Mapping[str, object]) -> int | None:
    status = result.get("status")
    return status if isinstance(status, int) else None


def _leaves(node: object) -> Iterator[str]:
    if isinstance(node, dict):
        for child in node.values():
            yield from _leaves(child)
    elif isinstance(node, list):
        for child in node:
            yield from _leaves(child)
    elif node is not None:
        yield str(node)


def mentions(body: str, values: Mapping[str, str]) -> bool:
    return _carried(body, values, quantifier=any)


def carries_every(body: str, values: Mapping[str, str]) -> bool:
    return _carried(body, values, quantifier=all)


def carries_in_slot(body: str, wanted: Mapping[str, str]) -> bool:
    if not wanted:
        return False
    return record_carrying(body, wanted) is not None


def record_carrying(body: str, wanted: Mapping[str, str]) -> dict[str, object] | None:
    if not wanted:
        return None
    try:
        parsed = json.loads(body)
    except ValueError:
        return None
    for record in _records(parsed):
        if all(record.get(slot) == value for slot, value in wanted.items()):
            return record
    return None


def _records(parsed: object) -> Iterator[dict[str, object]]:
    if isinstance(parsed, dict):
        yield parsed
        inner = parsed.get("data")
    elif isinstance(parsed, list):
        inner = parsed
    else:
        return
    if isinstance(inner, dict):
        yield inner
    elif isinstance(inner, list):
        yield from (row for row in inner if isinstance(row, dict))


def _carried(
    body: str, values: Mapping[str, str], *, quantifier: Callable[[Iterator[bool]], bool]
) -> bool:
    try:
        parsed = json.loads(body)
    except ValueError:
        return quantifier(bool(value) and value in body for value in values.values())
    leaves = set(_leaves(parsed))
    return quantifier(bool(value) and value in leaves for value in values.values())


def unreturned(body: str, values: Mapping[str, str]) -> tuple[str, ...]:
    if not values:
        return ()
    try:
        parsed = json.loads(body)
    except ValueError:
        return tuple(sorted(name for name, value in values.items() if value and value not in body))
    leaves = set(_leaves(parsed))
    return tuple(sorted(name for name, value in values.items() if value and value not in leaves))


@dataclass(frozen=True, slots=True)
class RunProof:
    run_id: str
    wrote: frozenset[int]
    verified: frozenset[int]

    @property
    def proves(self) -> bool:
        return bool(self.wrote) and self.wrote <= self.verified


def proven_runs(proofs: Sequence[RunProof]) -> int:
    return sum(1 for proof in proofs if proof.proves)


def earned_from(proofs: Sequence[RunProof]) -> bool:
    return proven_runs(proofs) >= K_EARNED_RUNS


def state_verified(verified_by: str) -> bool:
    return verified_by in STATE_BELTS
