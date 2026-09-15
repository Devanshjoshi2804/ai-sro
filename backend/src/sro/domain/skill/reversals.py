"""Taking back what a run made, where the evidence shows how.

A rig run creates records in a warehouse and nothing could take one back. The
guards in front of it -- a door that says when it is unsure, a list that proves
the first thing before doing the rest -- stop wrong records being MADE; none of
them helps with one that was.

**An undo is a job somebody has done, not a call this system invents.** The rig
knows what an operator was seen doing and nothing else. Where a tenant's
evidence shows somebody deleting the kind of record a job creates, that deleting
is itself a mined job and can be run; where it does not, there is no undo and
the honest thing is to say so and name what was made, so a person can go and do
it themselves.

Measured on this tenant's whole store the day this was written: three PUTs to
one address endpoint and **not one DELETE anywhere**. So this finds nothing
today, on purpose -- it is the mechanism, and it lights up the first time
somebody deletes a warehouse equipment type in front of the recorder.
"""

from __future__ import annotations

from collections.abc import Sequence

from sro.domain.execution.evidence import recorded_call
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.skill.workflow import Workflow

K_CREATED = 201
"""What a record being made looks like, and `repeats` says why it is 201 and
not "any mutation"."""

REMOVES = frozenset({"DELETE"})
"""What taking a record back looks like on the wire.

`DELETE` alone. A PUT that sets a flag to inactive is how several warehouses
retire a record, and it is also how every other edit is made -- reading one as
an undo would offer to "take back" a job by overwriting the record it made.
The day a tenant's evidence shows a disable being demonstrated as its own job,
that job is the undo and this is where it is recognised."""


def undoes(made: Workflow, gestures: dict[str, Gesture], among: Sequence[Workflow]) -> str | None:
    """Which job of this tenant's undoes what `made` creates, if any holds one.

    Matched on the endpoint and nothing else: a job that deletes the records
    another job creates is that job's undo, whatever either is called. Names
    are a model's, and an undo chosen by name is an undo chosen by a sentence
    somebody wrote about a job.

    The two endpoints are not the same string and must not be compared as one.
    A create addresses the collection -- `POST /wm/equipmentTypes` -- and a
    delete addresses one record in it -- `DELETE /wm/equipmentTypes/4471`,
    whose shape is the collection's plus the id. A DELETE to the collection
    ITSELF is not an undo of one record: it is whatever that warehouse means by
    emptying it, and this would be a poor place to find that out.
    """
    creates = _endpoint(made, gestures, statuses={K_CREATED})
    if creates is None:
        return None
    for other in among:
        if other.id == made.id:
            continue
        removes = _endpoint(other, gestures, methods=REMOVES)
        if removes is not None and removes == f"{creates}/*":
            return other.id
    return None


def _endpoint(
    workflow: Workflow,
    gestures: dict[str, Gesture],
    *,
    methods: frozenset[str] | None = None,
    statuses: set[int] | None = None,
) -> str | None:
    """The path shape this job's own write goes to, or None.

    `recorded_call` rather than every call the evidence holds, for the reason
    it was narrowed in the first place: a page's own background traffic is not
    what the operator did, and a job identified by a telemetry beacon's
    endpoint would be every job on that host.
    """
    for step in sorted(workflow.steps, key=lambda one: one.order):
        call = recorded_call(step, gestures)
        if call is None:
            continue
        if methods is not None and call.method.upper() not in methods:
            continue
        if statuses is not None and call.status not in statuses:
            continue
        return path_shape(call.url)
    return None
