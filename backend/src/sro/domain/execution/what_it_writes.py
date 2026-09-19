"""What a job would write, said before anybody presses it.

Item 6 closed the half that was silent about VALUES -- a request naming a field
the job has no parameter for is now said out loud on the card. What the card
still could not say is the write itself: *this will create a Customer Type
record on the SG site*. It names the values it holds; it does not name the act.

The difference does not bite on a deployment whose one job has one write. It
bites on the second job, and on any job with two writes in it, where "yes" is a
press against something nobody described -- and the moment to fix that is
before the second job arrives rather than after.

**Read off the evidence, like everything else here.** A step's own recorded
call is what `http.send` would replay and what `verify` reads a status from;
this is the same call, said in words. Nothing is guessed: a step with no
recorded mutation contributes nothing, and a job whose evidence has aged out
says nothing at all rather than something reassuring.

**What a method means is a convention, and the only one taken.** POST creates,
PUT and PATCH change, DELETE removes. That is the whole of the interpretation,
and it is the same convention `reversals.REMOVES` already rests on.
"""

from __future__ import annotations

from collections.abc import Mapping

from sro.domain.execution.evidence import READ_METHODS, recorded_call
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.shared.hosts import system_of
from sro.domain.skill.workflow import Workflow

DOES = {"POST": "create", "PUT": "change", "PATCH": "change", "DELETE": "remove"}
"""What each method does, in the word a person would use.

A method this does not know is left as itself -- upper case, as the wire had
it. Inventing a verb for one is how `PROPFIND` becomes "create"."""


def what_it_writes(workflow: Workflow, by_id: Mapping[str, Gesture]) -> list[dict[str, str]]:
    """Every write this job would make, in step order. Empty where it makes none.

    One entry per writing STEP and not per unique endpoint: a job that posts
    twice to one collection makes two records, and a card that said "creates a
    customerTypes record" once would be describing half of what the press does.
    """
    said: list[dict[str, str]] = []
    for step in sorted(workflow.steps, key=lambda one: one.order):
        call = recorded_call(step, by_id)
        if call is None:
            continue
        method = call.method.upper()
        if method in READ_METHODS:
            continue
        record = _what_it_addresses(method, path_shape(call.url))
        if not record:
            continue
        said.append(
            {
                "does": DOES.get(method, method),
                "record": record,
                "on": system_of(call.url) or "",
                "step": str(step.order),
            }
        )
    return said


def _what_it_addresses(method: str, shape: str) -> str:
    """What the record is called, out of the path the call went to.

    A create addresses the COLLECTION -- `POST /wm/customerTypes` -- and a
    delete addresses one member of it -- `DELETE /wm/customerTypes/GDD`. Same
    structural rule `reversals.undoes` compares on, and the reason it cannot be
    "the last segment": on a delete that is the record's own id, so a card
    would offer to remove a `GDD` rather than a customer type.

    `path_shape` blanks a segment carrying a digit, and `*` names nothing --
    so a segment it blanked is dropped here for the same reason the id is.
    """
    pieces = [one for one in shape.split("/") if one]
    # The member first, then the blanks. `path_shape` already blanked
    # `/customerTypes/4471` and left `/customerTypes/GDD` alone, so dropping
    # `*` first would take `customerTypes` off the numbered one and leave `wm`
    # -- a card offering to remove a `wm`.
    if method == "DELETE" and len(pieces) > 1:
        pieces = pieces[:-1]
    named = [one for one in pieces if one != "*"]
    return named[-1] if named else ""


__all__ = ["DOES", "what_it_writes"]
