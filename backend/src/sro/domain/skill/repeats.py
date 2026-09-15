"""A job whose middle is done once per thing on a list.

"Add these three equipment types" is one job. Until this existed the rig could
only say it was a job that adds ONE -- so a mail carrying three rows produced
one run that created the first, and an operator did the other two by hand while
watching a browser that had just proved it could do them.

**The list is a person's, and that is the whole of the first version.** The
items come from what somebody wrote -- a mail the browser matched, a sentence
typed into the panel -- so the count is a human's rather than a guess, and
getting the block wrong costs three wrong records instead of forty. The other
source, the list a page fetched for itself, is the more powerful one and is
deliberately not this: it needs the list call to have been captured, it needs a
re-read at run time, and its count is whatever the warehouse answers that day.
`domain/skill/loop.py` is that shape, for skills, and is where it goes when the
machinery here has done real work.

**The body is contiguous.** A block with a hole in it is two blocks somebody
has to be able to see separately, which is the same rule `Loop` states for the
same reason.

**Nothing here is the runner's decision.** What repeats is a fact about the
job; how many times is a fact about the request. A workflow with a `Repeat` and
a run given one item runs exactly like a workflow without one.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.domain.execution.evidence import recorded_call
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.workflow import Workflow

K_MOST_ITEMS = 25
"""How many times one run may do the body before a person is asked again.

Not a performance limit -- a limit on what one press can mean. An operator
pressing yes on "add these" has read a mail with a handful of rows in it; a
list of two hundred is either a mistake or a different decision, and the run
that would make two hundred records is not the one they authorised. The cap is
here rather than in the runner because it is part of what a repeat IS: the
runner asks the domain rather than carrying a number of its own.
"""


@dataclass(frozen=True, slots=True)
class Repeat:
    """The steps of a job that are done once per item, inclusive."""

    first_step: int
    last_step: int

    def __post_init__(self) -> None:
        if self.first_step < 0:
            raise InvariantViolation("a repeated block starts at a step that exists")
        if self.last_step < self.first_step:
            raise InvariantViolation("a repeated block ends before it begins")

    def covers(self, order: int) -> bool:
        return self.first_step <= order <= self.last_step

    @property
    def steps(self) -> int:
        return self.last_step - self.first_step + 1


K_CREATED = 201
"""What a record being made looks like on the wire.

The whole of the difference between a job that repeats and a page that talks.
Measured over this tenant's own jobs: the three that create something -- work
areas, customer types, warehouse equipment types -- each POST their endpoint
and get 201 back, while Gmail's `POST /mail/u/*/` came back 200 fourteen times
in one doing and creates nothing anybody asked for. A detector counting
mutations would have called drafting one message a job done fourteen times.
"""

K_SETTLE_S = 120.0
"""How long a pause ends a doing.

The same number `mine_lately` settles on and for the same evidence: a doing of
a real task runs 35 to 180 seconds of continuous gestures. Restated rather
than imported, because that one is about when a sweep may READ a tenant's day
and this one is about where one doing stops -- two questions that happen to
have one answer today, and a shared constant would hide the day they diverge.
"""


def detect(workflow: Workflow, gestures: dict[str, Gesture]) -> Repeat | None:
    """The steps this job did more than once in the doing it was mined from.

    `one_occurrence` has already struck every citation but one doing's by the
    time this runs, so the job in hand describes one pass through the work --
    and an operator who added three equipment types in a row produced exactly
    that: a job with the body once, and evidence with it three times.

    What is counted is the CREATE, not the clicks. Real evidence never repeats
    a gesture sequence exactly -- somebody scrolls, checks a row, clicks the
    grid between one record and the next -- and matching on sequences found
    nothing at all on this tenant's day. The endpoint the create goes to is the
    same every time, the recorder captured it, and 201 is what separates a
    record being made from a page talking to itself.

    Four things have to hold, and each one is a way this can be wrong:

    **The job creates something.** Its last mutating step came back 201. A 200
    is a page saving a draft, syncing a mailbox, or updating what is already
    there, and none of those is a thing to be done again per item.

    **It happened twice in ONE doing.** Not twice today: a task done once this
    morning and once after lunch is a task done twice, not a job with a
    repeated block. The doing is the citations' own span, grown outwards until
    a pause longer than `K_SETTLE_S`.

    **The creates are different records.** Two identical bodies are one record
    posted twice -- a double submit, a retry -- and repeating a body for a list
    of one thing typed twice is not a job, it is a mistake being learnt.

    **The body is on the system the create is on.** A job that reads a mail and
    then makes a record repeats the making, not the reading: the mail was read
    once and says what all three records are.
    """
    steps = sorted(workflow.steps, key=lambda step: step.order)
    creates = [
        (step, call)
        for step in steps
        if (call := recorded_call(step, gestures)) is not None and call.status == K_CREATED
    ]
    if not creates:
        return None
    made, call = creates[-1]
    cited = [gestures[one] for step in steps for one in step.cites if one in gestures]
    if not cited:
        return None

    wanted = f"{call.method.upper()} {path_shape(call.url)}"
    bodies = [
        request.request_body
        for gesture in _the_doing(cited, gestures)
        for request in gesture.requests
        if request.status == K_CREATED
        and f"{request.method.upper()} {path_shape(request.url)}" == wanted
    ]
    if len(bodies) < 2 or len({str(body) for body in bodies}) < 2:
        return None

    # The body is the run of steps up to the create that share its system: the
    # mail was read once and says what all of the records are.
    first = made.order
    for step in reversed([one for one in steps if one.order < made.order]):
        if step.system != made.system:
            break
        first = step.order
    return Repeat(first_step=first, last_step=made.order)


def _the_doing(cited: list[Gesture], gestures: dict[str, Gesture]) -> list[Gesture]:
    """Everything the operator did in the sitting these citations came from.

    Outwards from the citations rather than the citations themselves, because
    the thing being looked for is by definition what the job does NOT cite: the
    model summarised one pass and the second and third are past its last
    citation. It stops where the operator did, at a pause.
    """
    systems = {one.system for one in cited}
    on_hand = sorted(
        (one for one in gestures.values() if one.system in systems), key=lambda one: one.at
    )
    mine = {one.id for one in cited}
    doing: list[Gesture] = []
    for gesture in on_hand:
        if doing and gesture.at - doing[-1].at > K_SETTLE_S:
            if any(one.id in mine for one in doing):
                return doing
            doing = []
        doing.append(gesture)
    return doing if any(one.id in mine for one in doing) else []
