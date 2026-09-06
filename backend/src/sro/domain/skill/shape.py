"""What the extension matches a live tail against.

One entry per proven workflow: its shape -- (system, control identity, kind)
per cited gesture in step order, scrolls left out, the same key `identity.py`
resolves on -- and where in that shape each declared parameter was typed.
Computed from the cited gestures rather than read from `workflow.shape_key`, so
the parameter indices are indices into the very list the extension will walk.

Nothing here carries a typed value. A shape is control identities, hosts and
parameter *names*; the values that went into those controls stay in the
gestures, which is the only place they were ever allowed.

The queries that gather the evidence -- the proven workflows, the held tally,
the cited gestures and this job's own offers -- live in the application layer.
What is left here is the arithmetic: given the pairs and the counsel, the shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass

from sro.domain.execution.evidence import allowlist, primary_gesture
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.identity import shape_key, target_identity
from sro.domain.shared.hosts import system_of
from sro.domain.skill.learned import control_name
from sro.domain.skill.offers import K_OFFER_AFTER, Counsel
from sro.domain.skill.workflow import Step, Workflow


@dataclass(frozen=True, slots=True)
class Shape:
    id: str
    title: str
    starts_on: str | None
    hosts: list[str]
    shape: list[list[str]]
    parameters: list[dict[str, object]]
    held_runs: int = 0
    offer_after: int = K_OFFER_AFTER
    quiet_until: str | None = None
    """Set when the asking browser refused this job three times running: the
    shape is still served -- the list stays whole and cacheable, and an open
    offer on the job can still tell diverging from finishing -- and
    `recognise.js` declines to offer it until then."""

    def as_json(self) -> dict[str, object]:
        return asdict(self)


def cited_pairs(workflow: Workflow, by_id: Mapping[str, Gesture]) -> list[tuple[Gesture, Step]]:
    """The cited gestures in step order, each still paired with the step that
    cited it. The pairing is what `typed_at` needs and what a flat list of
    gestures throws away."""
    return [
        (by_id[cited], step)
        for step in sorted(workflow.steps, key=lambda s: s.order)
        for cited in step.cites
        if cited in by_id
    ]


def typed_at(cited: list[tuple[Gesture, Step]], parameter: dict[str, object]) -> int | None:
    """Where in the shape this parameter was typed, by the step that declares it.

    Scanning every cited gesture for the first value match binds the wrong
    control on any search-then-create flow: the code is typed into the search
    box before it is typed into the field the workflow is actually filling, so
    the extension would fill the search box and stop. Only the step whose
    `parameters` names this one is asked.
    """
    name = str(parameter["name"])
    values = parameter.get("seen_values")
    seen: set[str] = {str(v) for v in values} if isinstance(values, list) else set()
    for index, (gesture, step) in enumerate(cited):
        if name in step.parameters and gesture.action.value in seen:
            return index
    # A parameter learned across doings (`parameters_across`) is recorded on
    # the workflow and on no step: it is named after the control it was typed
    # into, so the control with that name, typing one of its values, is where
    # it sits. Narrower than a value scan -- the search box is not named
    # `workArea` -- and without it every learned parameter had no index and
    # no offer could lift its value from a tail.
    for index, (gesture, _) in enumerate(cited):
        if control_name(gesture) == name and gesture.action.value in seen:
            return index
    return None


def walkable(cited: list[tuple[Gesture, Step]]) -> list[tuple[Gesture, Step]]:
    """The cited pairs the extension can actually match on.

    A scroll is not one: `recognise.js` drops one before it is ever written
    into the tail, so a served shape carrying one could not be matched at any k
    -- a job whose first triple is a scroll could never be offered at all.
    Dropped before both the shape and the parameter indices are computed, so
    `at` indexes the very list the extension walks.
    """
    return [pair for pair in cited if target_identity(pair[0]) != "anon|scroll"]


def shape_of(
    workflow: Workflow, cited: list[tuple[Gesture, Step]], *, held: int, advice: Counsel
) -> Shape | None:
    """One workflow as the extension needs it, or None when it cannot be
    served: nothing cited, or a start its own evidence never names."""
    if not cited:
        return None
    gestures = [gesture for gesture, _ in cited]
    by_id = {g.id: g for g in gestures}
    first_step = min(workflow.steps, key=lambda s: s.order)
    first = primary_gesture(first_step, by_id) or gestures[0]
    starts_on = first.page_url or first.url
    hosts = sorted(allowlist(workflow, by_id))
    # `starts_on` is the tab's origin; `hosts` is what the evidence names,
    # which is the frame's. When they disagree the extension would be sent
    # to open an origin no cited gesture ever proved -- so it is not sent.
    if system_of(starts_on) not in hosts:
        return None
    # `starts_on` and `hosts` are read off the whole of the evidence above:
    # where the job begins is a fact about the recording, not about what can
    # be matched.
    walk = walkable(cited)
    return Shape(
        id=workflow.id,
        title=workflow.title,
        starts_on=starts_on,
        hosts=hosts,
        shape=[list(triple) for triple in shape_key([g for g, _ in walk])],
        parameters=[
            {"name": str(p["name"]), "at": typed_at(walk, p)}
            for p in workflow.parameters
            if isinstance(p, dict) and p.get("name")
        ],
        held_runs=held,
        # What this job's own offers say: resting on this browser, or offered
        # later. Capped at the last gesture but one, which is as late as
        # `recognise.js` can offer: a job that diverges even there keeps
        # diverging, on record.
        offer_after=max(K_OFFER_AFTER, min(advice.offer_after, len(walk) - 1)),
        quiet_until=advice.quiet_until,
    )
