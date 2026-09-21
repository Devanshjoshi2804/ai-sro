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

import json
from collections.abc import Mapping, Sequence

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


def identifies(undo: Workflow, gestures: Mapping[str, Gesture]) -> frozenset[str]:
    """Which fields of a record the undo's own delete addresses it by.

    **Read off the delete, never guessed from a name.** A DELETE addresses one
    member of a collection -- `DELETE /wm/customerTypes/GDD` -- and on this
    platform it carries the record it is removing as its BODY. So the fields
    that could identify are the ones whose value is the segment in the path,
    and no part of that is `customerType` being the singular of
    `customerTypes`, which is the correspondence `write_plan` refuses at
    length.

    A SET, because the real answer is not one field. Measured on the
    deployment 2026-09-19, the delete of `GDD` carries it twice -- as
    `customerType` and as `resourceId` -- and either would address the record.
    What settles it is the other side: `addresses` keeps whichever of these the
    CREATE recorded making, and a run's `made` holds `customerType` and no
    `resourceId`.

    Empty where the delete carried nothing, which is every platform that
    answers a delete with an empty request, and then nothing has changed: one
    record named one way, or no button.
    """
    for step in sorted(undo.steps, key=lambda one: one.order):
        call = recorded_call(step, gestures)
        if call is None or call.method.upper() not in REMOVES:
            continue
        member = _pieces(path_shape(call.url))
        if not member:
            return frozenset()
        addressed = member[-1]
        body = call.request_body.text if call.request_body is not None else None
        return frozenset(
            key
            for key, value in _record(body).items()
            if value == addressed and key.strip() and value.strip()
        )
    return frozenset()


def asks_for(undo: Workflow) -> str | None:
    """What the undo calls the value it needs, in its own vocabulary.

    The press has to speak the JOB's language, not the warehouse's. `Delete a
    Customer Type` declares one parameter and it is called `Customer Type` --
    the screen's label, which is how every mined job names what varies -- while
    the record it deletes is keyed `customerType` in the body. A press that
    sent the body key would name a parameter this job does not have, and the
    run would refuse it as a value nobody supplied.

    One parameter or nothing. A delete that varies two things is a delete this
    cannot fill from one created record, and guessing which of them wants the
    id is the wrong kind of guess to make with a DELETE.
    """
    named = [
        str(one["name"]).strip()
        for one in undo.parameters
        if isinstance(one, Mapping) and str(one.get("name", "")).strip()
    ]
    return named[0] if len(named) == 1 else None


def _record(text: str | None) -> dict[str, str]:
    """A body's top-level string values, keyed. The envelope first, as
    everything that reads a Blue Yonder body does."""
    if not text:
        return {}
    try:
        document = json.loads(text)
    except ValueError:
        return {}
    if not isinstance(document, dict):
        return {}
    inner = document.get("data")
    record = inner if isinstance(inner, dict) else document
    return {
        key: value.strip()
        for key, value in record.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def addresses(
    made: Sequence[Mapping[str, str]], by: frozenset[str] = frozenset()
) -> tuple[str, str] | None:
    """Which record an undo would address, out of what a run read back.

    The mapping `undo` has said it lacked since it was written: *what a press
    would have to do -- address each created record by whatever the warehouse
    called it -- is a mapping nothing here has evidence for, and a wrong
    mapping deletes the wrong record.* It has evidence for it now. A step that
    created something records what the warehouse called it, and `made_by` keeps
    the identifying fields and nothing else.

    **Exactly one record, named by exactly one field.** Everything else is a
    refusal, and each is the same refusal wearing a different hat:

    - A run that made two records would need two deletes, and an undo that
      takes back half of what a run did is worse than none -- somebody presses
      it, sees the card go quiet, and believes the warehouse is back where it
      started.
    - A record named two ways is a record this cannot name at all. `made_by`
      keeps `id`, `code`, `name`, `number` and `key`, and a warehouse that
      answered with two of them has not said which one addresses it.

    A wrong guess here removes somebody else's record, which is the one thing
    an undo must never do.
    """
    named = [one for one in made if one]
    if len(named) != 1:
        return None
    only = named[0]
    if by:
        # The delete's own evidence named the fields it addresses a record by,
        # so a record carrying more than one thing is no longer a record named
        # two ways -- it is a record named once and described alongside.
        #
        # The intersection, and it has to be exactly one. On the deployment the
        # delete addresses `GDD` as both `customerType` and `resourceId` and
        # the create records only the first, so one side narrows the other.
        # Two survivors would be two names for one record again, and this
        # refuses that for the reason it always has.
        shared = [key for key in by if only.get(key, "").strip()]
        if len(shared) != 1:
            return None
        return (shared[0], only[shared[0]].strip())
    if len(only) != 1:
        return None
    ((only_field, names),) = only.items()
    return (only_field, names.strip()) if names.strip() else None


def undoes(made: Workflow, gestures: dict[str, Gesture], among: Sequence[Workflow]) -> str | None:
    """Which job of this tenant's undoes what `made` creates, if any holds one.

    Matched on the endpoint and nothing else: a job that deletes the records
    another job creates is that job's undo, whatever either is called. Names
    are a model's, and an undo chosen by name is an undo chosen by a sentence
    somebody wrote about a job.

    The two endpoints are not the same string and must not be compared as one.
    A create addresses the collection -- `POST /wm/equipmentTypes` -- and a
    delete addresses one record in it -- `DELETE /wm/equipmentTypes/4471`,
    whose path is the collection's plus the id. A DELETE to the collection
    ITSELF is not an undo of one record: it is whatever that warehouse means by
    emptying it, and this would be a poor place to find that out.

    **One more segment, and never `path_shape`'s `*`.** That function blanks a
    segment carrying a DIGIT, which is right for `/equipmentTypes/4471` and
    silent for `/customerTypes/GDD` -- so the id survived the blanking, the
    delete's shape carried the record it happened to be demonstrated on, and it
    could never equal `collection/*`. Measured on this deployment 2026-09-19:
    the tenant has held `Create a Customer Type` and `Delete a Customer Type`
    for weeks, and this answered None every time.

    Comparing the SEGMENTS needs no rule about what an id looks like, which is
    the right amount to know: that a delete addresses one member of the
    collection a create posts to is structural, and what that member is called
    is the warehouse's business.
    """
    creates = _endpoint(made, gestures, statuses={K_CREATED})
    if creates is None:
        return None
    collection = _pieces(creates)
    if not collection:
        return None
    for other in among:
        if other.id == made.id:
            continue
        removes = _endpoint(other, gestures, methods=REMOVES)
        if removes is None:
            continue
        member = _pieces(removes)
        if len(member) == len(collection) + 1 and member[:-1] == collection:
            return other.id
    return None


def _pieces(shape: str) -> list[str]:
    """A path shape in segments, with the empties dropped."""
    return [one for one in shape.split("/") if one]


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
