"""A14: verify against state, and only then against a picture -- and D2: when a
job has earned the right to write without being asked.

Measured over the 643 tasks of the WebVoyager benchmark, a validator reading
the run's own text -- what the calls returned -- scored 84.24% against 70.04%
for one reading screenshots, with over 84% agreement with human annotators; a
screenshot read beside the agent's final answer still only reached 83.00%. So: the response the
command itself returned first, a confirming read the cited evidence shows the
page performs second, and the screenshot last and least. A green toast is the
weakest of the three and the easiest to be wrong about.

arXiv:2410.00689, Tables 1 and 2. Corrected twice: the figures that stood here
first (86.9/78.8, 94%, "192 of 321") are in no version of that paper, and the
first correction then misattributed the denominator -- 322 is the subset used
for the self-validation experiment, not for these tables. `verify.py` carries
the whole account.

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
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field

from sro.domain.execution.evidence import READ_METHODS, recorded_call
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step

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
class StepVerdict:
    """One step's verify, and which belt decided it. Named for the step because
    `sro.domain.skill.track_record.Verdict` is the other one -- a whole run's
    standing, counted over many of these."""

    state: str  # held | failed | unclear
    by: str  # status | read | screen | none
    reason: str
    answer: Answer | None = None

    made: Mapping[str, str] = field(default_factory=dict)
    """What the warehouse called the record this step created, where it made
    one and said so. Empty for every step that created nothing, which is most
    of them -- and for a create whose answer named nothing this can read.

    A run that made three records has to be able to say which three, or nobody
    can go and look at them."""


def expected_statuses(step: Step, by_id: Mapping[str, Gesture]) -> set[int]:
    """Every status the call this step replays actually came back with.

    The call this step replays is `recorded_call`'s, so that endpoint is the
    only one whose statuses mean anything here. An earlier version took every
    mutating call on every cited gesture, which let a page's own background
    traffic into the set a run is verified against: on four steps across both
    real tenants -- `new`'s `Create a Customer Type` step 5, acme's steps 1 and
    6 of the same job, and acme's `Create an Activity Code` step 7 -- the
    evidence fires a 201 create AND a 200 keep-alive or telemetry batch, and
    the set came out `{200, 201}`. A replayed create that came back 200 instead
    of 201 would then be held by rung 1 of `verify` on the strength of a
    performance beacon's status code, with the read-back and the screenshot
    never asked. Narrowed to the replayed endpoint, those four steps give
    `{201}` and a 200 falls through to the rest of the ladder.

    Only a mutation names a status here. If this step's evidence made no write
    the set is empty, and `verify` falls back to plain 2xx -- a GET's 204
    counted here would teach it that 204 is what a write looks like.

    A request with a `failure_reason` never completed, so whatever status it
    carries is not a status the warehouse returned -- see `origin_of`, which
    learned the same thing about picking a host off a dead call.
    """
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

    ANY value, because this is asked AFTER the write: the read is being shown
    the record that was just made, and one value of it coming back is the
    record coming back. `carries_every` is the same question asked before the
    write, where any is the wrong quantifier and the difference is a write
    that never happens.
    """
    return _carried(body, values, quantifier=any)


def carries_every(body: str, values: Mapping[str, str]) -> bool:
    """Whether the read shows ALL of what this run would write.

    The precondition's rule, and it has to be every one of them. A job carries
    values that change from run to run and values that do not -- an order's
    reference, a facility, a site -- and `any` reads a record whose UNCHANGED
    half matches as the record this run was going to create.

    Measured end to end, live, on 2026-09-15: four runs of a three-step job
    that types a new client code and the same reference each time. The
    confirming read answered the PREVIOUS record, its `reference` matched, and
    every one of the four skipped its write and reported `held` -- 0 writes
    reached the page across four runs that each said they had done the job.
    Nothing in 3000 unit tests saw it, because nothing asked what happens when
    one of the values is the same as last time.
    """
    return _carried(body, values, quantifier=all)


def carries_in_slot(body: str, wanted: Mapping[str, str]) -> bool:
    """Whether the read shows each value in the KEY the plan put it in.

    What `carries_every` above cannot ask. It searches the whole record for the
    value, so a job that fills two fields is confirmed by a record that carries
    the right code in the wrong place -- and it is confirmed just as happily by
    a record that carries the code somewhere the plan never wrote.

    Measured over the 94 recorded creates whose request and response are both
    JSON objects: **16 send a value that appears nowhere in the answer**, every
    one of them a `…Description` key where the form posts the code and the
    server stores the resolved label. `carries_every` fails those records, and
    they are correct records -- a failed write stops the run and empties the
    job's register of verified effects. `wanted` is `WritePlan.confirm`, which
    is already narrowed to the slots the demonstration's own answer echoed
    back unchanged, so a slot the server rewrites is never asked about.

    Empty `wanted` is False: nothing was checked, so nothing was shown. The
    caller decides what to do with a belt that could not run -- `verify` does
    not reach here at all for an empty one, and holds on the status instead.
    """
    if not wanted:
        return False
    return record_carrying(body, wanted) is not None


def record_carrying(body: str, wanted: Mapping[str, str]) -> dict[str, object] | None:
    """The record in this answer that carries every one of these values, or None.

    What `carries_in_slot` asks, and what the result card reads. A run that
    made a record has to be able to say WHICH record, and on this endpoint
    `made_by`'s suffix rule cannot: the identifier is `customerType`, which
    ends in none of `id`/`code`/`name`/`number`/`key`. The plan already knows
    which keys this job varies, so the row those keys found is the row to show.
    """
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
    """The records an answer holds, whether it is one or a page of them.

    A confirming read is whatever GET the page made after its write, and on the
    system this was built for that is the COLLECTION, not the created row:
    measured live 2026-09-16, the read after `POST /wm/customerTypes` is
    `GET /wm/customerTypes?siteId=SG&…`, a list of every customer type. A rule
    that could only read a single record called a 201'd create failed because
    it was looking for `customerType` on the envelope of a list.

    So: the document itself, what is inside its `data` envelope -- the shape
    112 of the 114 recorded successful writes carry -- and, where that is a
    list, each row of it.

    `any` over records and `all` over slots, and the pairing is the point. A
    record that carries EVERY slot this run filled is the record this run
    created; a list in which one row matches the code and another matches the
    description shows neither. The whole-body search this replaced could not
    tell those apart -- it flattened the page to a set of leaves, so a
    collection confirmed a write as long as the values existed anywhere in it,
    including in two different rows and including in the row the demonstration
    made.
    """
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
    """The names this run supplied that the read did not come back carrying.

    `mentions` asks whether ANY of them came back, and holds on one -- which is
    right, and is why this exists beside it rather than instead of it. A record
    read after a write is being asked "are you there", and one value answering
    is the record answering. Requiring ALL of them was tried and measured
    wrong: of 94 recorded creates, 16 send a value that appears nowhere in the
    answer -- every one a `...Description` key holding the label its code
    resolved to -- so `carries_every` failed roughly one correct create in six
    and un-earned a job for being right.

    But a warehouse that silently shortens a field answers the same way. Send a
    code and a sixty-character description, have the description truncated on
    save, and the code comes back, `mentions` is satisfied, and the step holds
    by `read`. Every belt in the chain then agrees, because every one of them
    compares the record to ITSELF: the status is the server's, the read-back is
    the record as stored, and a picture of the grid row looks right to a model
    with no idea what was asked for.

    So the step still holds -- one value back is the record back -- and what
    did NOT come back is named. A truncation stops being invisible without a
    correct write being failed for it.

    Names, never values: this is read by a panel and a log.
    """
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
