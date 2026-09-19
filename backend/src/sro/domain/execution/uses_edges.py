"""Which earlier step a later one took its value FROM, read off the evidence.

`Step.uses` is CrewAI's `Task.context` and it has existed with nothing to write
it. This writes it, and the rule is the one the whole codebase keeps: the edge
is discovered rather than guessed, and where the evidence does not settle it
nothing is claimed.

**A value the SERVER made.** The signal is not "step five typed something step
two also had" -- a job that types one code into two screens would read as a
dependency, and it is one parameter typed twice. It is "step five typed
something that did not exist until step two was answered": a key in step two's
response record whose value was not in step two's own request. An id the
warehouse minted. The later step could not have known it any other way, and
that is precisely what a dependency is.

**Per doing, and every doing.** A generated id differs between demonstrations
-- record 111 on Tuesday and 222 on Wednesday -- so the match is made inside
one doing and required in all of them. That is what makes this strong rather
than a coincidence: a constant that happened to appear twice matches once and
fails the next doing, and two doings that both track the answer they were given
are not a coincidence anybody has to rule out.

Cites are paired by POSITION, which is how they are written: a step cites one
gesture per doing, in the order the doings happened, and `_bodies_of` reads
them the same way. A step whose cites do not line up with another's -- a
different number of doings -- contributes only the positions both have.

Pure. Nothing here reads a store, and nothing here decides what a run does with
an edge; `run_workflow._what_earlier_steps_made` is that half.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from sro.domain.execution.evidence import READ_METHODS
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.skill.workflow import Step, Workflow

K_SHORTEST = 3
"""How long a value must be before it can carry a dependency.

`0`, `-1` and `SG` appear all over a warehouse form, and an edge drawn from one
is an edge drawn from a coincidence. Three characters is the shortest thing an
id ever is, and short enough to keep the real ones.
"""


def uses_edges(workflow: Workflow, by_id: Mapping[str, Gesture]) -> dict[int, list[int]]:
    """For each step, the earlier steps whose answer it used. Empty where none.

    Only backwards, which needs no check here -- the loop only ever looks at
    steps already passed -- and `checks.validate` refuses a forward edge anyway,
    so a producer that emitted one would be caught rather than trusted.
    """
    ordered = sorted(workflow.steps, key=lambda one: one.order)
    made: dict[int, list[frozenset[str]]] = {step.order: _made_by(step, by_id) for step in ordered}
    edges: dict[int, list[int]] = {}
    for position, step in enumerate(ordered):
        took = _took(step, by_id)
        if not any(took):
            continue
        for earlier in ordered[:position]:
            # Never a step that stands on the same evidence. Two steps citing
            # one gesture are one thing the operator did, narrated twice -- and
            # `_made_by` and `_took` then read the SAME call from both sides,
            # so the "dependency" is a step on itself. Measured on `rigproof`
            # 2026-09-19: the only edge in three tenants' stores was exactly
            # this, `Create a client` step 2 on step 1, both citing one click.
            if set(step.cites) & set(earlier.cites):
                continue
            if _every_doing_took_it(took, made.get(earlier.order, [])):
                edges.setdefault(step.order, []).append(earlier.order)
    return edges


def _every_doing_took_it(took: Sequence[frozenset[str]], made: Sequence[frozenset[str]]) -> bool:
    """Whether every doing this pair shares took a value that doing produced.

    `all`, and never over an empty list: a pair with no doing in common has
    demonstrated nothing about each other, and `all(())` is True, which would
    make an edge out of two steps that were never recorded together.
    """
    shared = [(one, other) for one, other in zip(took, made, strict=False) if one and other]
    if not shared:
        return False
    return all(one & other for one, other in shared)


def _made_by(step: Step, by_id: Mapping[str, Gesture]) -> list[frozenset[str]]:
    """Per doing, the values this step's answer carried that its request did not.

    The difference is the whole rule. A value the request sent and the response
    gave back is the operator's own coming round again; one only the response
    has is one the warehouse minted, and nothing downstream could have known it
    before this step ran.

    One entry per DOING and not per call, so it pairs with `_took`: a doing is
    what the two steps share, and a step whose gesture made three requests made
    them all in the same doing.
    """
    made: list[frozenset[str]] = []
    for gesture in _doings(step, by_id):
        minted: set[str] = set()
        for call in _writes(gesture):
            back = {value for _, value in _record(_text(call.response_body))}
            minted |= back - _sent(call)
        made.append(frozenset(minted))
    return made


def _sent(call: Call) -> frozenset[str]:
    return frozenset(value for _, value in _record(_text(call.request_body)))


def _text(body: object) -> str | None:
    said = getattr(body, "text", None)
    return said if isinstance(said, str) else None


def _took(step: Step, by_id: Mapping[str, Gesture]) -> list[frozenset[str]]:
    """Per doing, the values this step put in: typed into a control, or sent.

    Both, because a step reaches a value two ways and the evidence records them
    differently -- an operator pasting an id into a box, and a page posting one
    it held.
    """
    took: list[frozenset[str]] = []
    for gesture in _doings(step, by_id):
        values = set()
        typed = gesture.action.value
        # No length rule here, deliberately. `_record` keeps the one that
        # matters, on the side that PRODUCES a value -- so nothing short can
        # ever be matched however it arrived, and a second copy of the rule
        # here would be a line no test can reach and a number to keep in step.
        if isinstance(typed, str) and typed.strip():
            values.add(typed.strip())
        for call in gesture.requests:
            values.update(_sent(call))
        took.append(frozenset(values))
    return took


def _doings(step: Step, by_id: Mapping[str, Gesture]) -> list[Gesture]:
    return [by_id[cited] for cited in step.cites if cited in by_id]


def _writes(gesture: Gesture) -> list[Call]:
    """The calls that could have MINTED something: mutations, with an answer.

    A read is excluded, and it is the case that matters rather than a tidiness.
    The confirming read-back this system relies on everywhere -- `GET
    /api/orders?latest=1` after the POST -- answers with exactly the record
    that was just sent, and its own request has no body to subtract, so every
    value the operator typed reads as a value the warehouse minted. That is the
    other half of the same measurement: on `rigproof`, `OFFER-1` and `PO-99001`
    were typed into the form and came back as the server's own work.
    """
    return [
        call
        for call in gesture.requests
        if call.response_body is not None and call.method.upper() not in READ_METHODS
    ]


def _record(text: str | None) -> list[tuple[str, str]]:
    """A body as its leaf values, keyed, flattened one level.

    Strings only and never short ones: an edge drawn from `0` or `SG` is an
    edge drawn from a coincidence.
    """
    if text is None:
        return []
    try:
        document = json.loads(text)
    except ValueError:
        return []
    if not isinstance(document, dict):
        return []
    inner = document.get("data")
    record = inner if isinstance(inner, dict) else document
    return [
        (key, value.strip())
        for key, value in record.items()
        if isinstance(value, str) and len(value.strip()) >= K_SHORTEST
    ]


__all__ = ["K_SHORTEST", "uses_edges"]
