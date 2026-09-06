"""A14: verify against state, and only then against a picture -- and D2: when a
job has earned the right to write without being asked.

A state-grounded verifier scored 86.9% against 78.8% for one reading
screenshots, with human agreement at 94%. Most completions leave their proof
off-screen -- artifact verification was 192 of 321 tasks. So: the response the
command itself returned first, a confirming read the cited evidence shows the
page performs second, and the screenshot last and least. A green toast is the
weakest of the three and the easiest to be wrong about.

The earning rule reads the same order from the other end. Autonomy is earned by
verified effect, not by counting runs: a write counts only when the verifier
decided `held` by state -- a status the server answered, or a read that showed
the record -- and never by a picture. A failed write un-earns the job, and the
next runs ask again.

Pure: the belts decide, and the sending, the asking and the counting of rows
live outside. `verify` itself -- the probe on the wire and the model that reads
the picture -- is the application's, and asks these questions.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass

from sro.domain.execution.evidence import recorded_call
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step

_READ_METHODS = ("GET", "HEAD", "OPTIONS")

K_WEAK_LOCATORS = frozenset({"css_path", None})
"""A step that only ever matches on the last fallback is a step about to break.
The run succeeds and the step is flagged stale."""

K_EARNED_RUNS = 3
"""Live runs whose every write verified by state before the tap goes away.
Three is a job that worked on three different days' values, not a job that
worked once."""

STATE_BELTS = ("status", "read")
"""The two verdicts that saw the state itself. `screen` is a model reading a
picture, and a picture is not an effect."""

SCREEN_SCHEMA: dict[str, object] = {
    "type": "object",
    # held first, why last: decide, then explain.
    "properties": {"held": {"type": "boolean"}, "why": {"type": "string"}},
    "required": ["held", "why"],
    "propertyOrdering": ["held", "why"],
}

SCREEN_INSTRUCTIONS = """You are checking whether one step of a warehouse job was actually done.
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
            if request.method.upper() in _READ_METHODS:
                continue
            if request.status is not None and not request.failure_reason:
                found.add(request.status)
    return found


def confirming_read(step: Step, by_id: Mapping[str, Gesture]) -> Call | None:
    """A GET a cited gesture made after its write, and that came back: the read
    the page performs to show the result, which is the hidden state a run can
    ask for again.

    Same completion guard as `expected_statuses`, for the reason `origin_of`
    already learned -- the real capture has a GET to a dead host arriving one
    millisecond after the write, and a probe aimed there proves nothing.

    A call with no `started_at` is a call at an unknown time. It cannot be shown
    to have come after the write, and "after the write" is the whole claim, so
    it is not the read -- the same strictness that makes the same instant not
    after.

    ponytail: "first completed GET after the write" still admits a stream, a
    beacon or a health poll; pick by response shape if that starts costing.
    """
    call = recorded_call(step, by_id)
    if call is None or call.method.upper() in _READ_METHODS or call.started_at is None:
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
    """The status out of the browser's reply, when it gave one."""
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
    """Whether the read came back carrying a value this run supplied.

    Leaf equality, not substring: the capture's own order list answers
    `{"orders": [{"id": "ORD-1"}]}`, and a run value of "1" is inside that
    string without being in it. A length floor cannot save the substring test
    either -- this tenant's real work-area codes are two characters. Substring
    is kept only for a body that is not JSON, where there are no leaves to
    compare.
    """
    try:
        parsed = json.loads(body)
    except ValueError:
        return any(value and value in body for value in values.values())
    leaves = set(_leaves(parsed))
    return any(value and value in leaves for value in values.values())


@dataclass(frozen=True, slots=True)
class RunProof:
    """One live run that held, reduced to the two sets the rule compares:
    the steps that wrote, and the steps a state belt verified."""

    run_id: str
    wrote: frozenset[int]
    verified: frozenset[int]

    @property
    def proves(self) -> bool:
        """A run with no write proves nothing about writing. One with a write
        a state belt did not see proves the opposite."""
        return bool(self.wrote) and self.wrote <= self.verified


def earned_from(proofs: Sequence[RunProof]) -> bool:
    """Whether a job may write unasked: `K_EARNED_RUNS` live held runs, each
    with every write verified by state (`STATE_BELTS`). Effects decided by
    screen are never recorded, so `verified` here is state by construction."""
    return sum(1 for proof in proofs if proof.proves) >= K_EARNED_RUNS


def state_verified(verified_by: str) -> bool:
    """The gate `record_effect` keeps: only a state belt's verdict is an effect."""
    return verified_by in STATE_BELTS
