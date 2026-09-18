"""Which mined job takes back what this one made, if any does.

`application/execution/reversal.py` answers this for a taught SKILL and has
since skills existed. A rig run has no answer at all -- the panel says so in
its own words: *a run the rig drove has neither a reversal nor anywhere to send
"It's wrong", so the card offers neither, rather than offering both and failing
on the press.* Every record these runs make is a record nobody can take back
from the surface they made it on.

The three facts are that module's, unchanged, because the argument is the same
one: **a visible undo is the strongest thing an agentic surface has, because
trust is knowing you can recover from a mistake. It is also where this design
could most easily begin guessing, so it does not.**

  - the run's write was a POST to some collection, and
  - a mined job in this tenant DELETEs a record of that collection, and
  - the run read back the one identifier that names it.

**Matched on the path and never on `url_shape`.** That function blanks a
segment carrying a DIGIT, which is right for `/addresses/A00022791` and wrong
here: this deployment's customer types are `GGD` and `GDD`, so the id survives
the blanking and two deletes of two records look like two different endpoints.
What is checked instead is structural and needs no rule about what an id looks
like -- the delete's path is the create's path with exactly one more segment on
it, which is what deleting a member of a collection IS.

**One identifier or none.** A run that read back two is a run where nothing here
can say which names the record, and a delete addressed to a guess is worse than
no undo at all -- the record it removes would be somebody else's.

Most jobs will have no undo for a long time, because nobody demonstrates
deleting things. That is honest, and it is `reversal.py`'s own note: the
fallback is the operator fixing it while we watch, which is what they were
going to do anyway.

Pure. Nothing here performs anything, and an undo is offered rather than taken.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Step, Workflow


@dataclass(frozen=True, slots=True)
class TakesItBack:
    """The job that undoes another, and what it will address."""

    workflow_id: str
    title: str
    removes: str
    """What the delete step says it does, in the words the miner gave it. The
    panel puts this in front of somebody BEFORE the press, for ADR 014's
    reason: a press that nobody could read is not consent."""

    field: str
    names: str
    """Which identifier the record is named by, and what it is. Both, because
    `customerType: GGD` says what the delete will address and `GGD` alone does
    not."""


def takes_back(
    *,
    made: Mapping[str, str],
    wrote: str,
    made_by: str,
    library: Sequence[Workflow],
    by_id: Mapping[str, Gesture],
) -> TakesItBack | None:
    """The mined job that deletes what this run created, or None.

    `made` is what the run read back, `wrote` the url it POSTed to, and
    `made_by` the job that did it -- a job that deletes what it creates is not
    an undo of itself, and nothing should offer it as one.
    """
    if len(made) != 1:
        return None
    ((field, names),) = made.items()
    if not names.strip() or not wrote.strip():
        return None
    collection = _segments(wrote)
    if not collection:
        return None
    for job in library:
        if job.id == made_by:
            continue
        step = _deletes_a_member_of(collection, job, by_id)
        if step is not None:
            return TakesItBack(
                workflow_id=job.id,
                title=job.title,
                removes=step.says,
                field=field,
                names=names.strip(),
            )
    return None


def _deletes_a_member_of(
    collection: list[str], job: Workflow, by_id: Mapping[str, Gesture]
) -> Step | None:
    """The step of this job whose evidence DELETEs a member of that collection.

    One more segment and the same prefix, which is what deleting a member of a
    collection is. Not `url_shape`: it blanks a segment that carries a digit,
    and an id that carries none survives it -- so the shape of a delete would
    include the record it happened to be demonstrated on.
    """
    for step in sorted(job.steps, key=lambda one: one.order):
        for cited in step.cites:
            gesture = by_id.get(cited)
            if gesture is None:
                continue
            for call in gesture.requests:
                if call.method.upper() != "DELETE":
                    continue
                path = _segments(call.url)
                if len(path) == len(collection) + 1 and path[:-1] == collection:
                    return step
    return None


def _segments(url: str) -> list[str]:
    """A url's path, in pieces, with the empties dropped.

    The host is deliberately not compared here: two jobs mined from one
    warehouse are on one host by construction, and a job whose evidence spans
    two systems is refused long before this by `checks.validate`.
    """
    return [one for one in urlsplit(url).path.split("/") if one]


__all__ = ["TakesItBack", "takes_back"]
