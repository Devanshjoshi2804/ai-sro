"""What varies between two doings of one job.

A parameter cannot be found in a single occurrence. Shown one doing of "Create
Work Activity TEST1", nothing in the evidence says whether `TEST1` is the name
of this activity or the name of every activity -- and asking a model produces a
guess wearing the clothes of a finding. Measured: across the eight workflows
mined from 170 hours of real capture, every `parameters` list came back empty,
which was the honest answer to a question nobody had asked.

Two doings answer it. What the operator typed differently is what the job takes
as input; what they typed identically is part of the job. That is arithmetic
over evidence rather than an opinion about it.

This is available here because `identity.resolve` already finds the pairs:
`same_job` means one job matched by SHAPE while citing different gestures --
two occurrences, which is exactly what a diff needs. Measured on the real
corpus, thirteen of fourteen second-pass matches came through shape rather than
citation overlap, so the pairs are the common case rather than the rare one.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from rig.records import Gesture, Intent
from rig.values import typed_values
from rig.workflows import Workflow

K_MIN_OCCURRENCES = 2
"""Doings needed before anything is called a parameter.

One is a recording. The name exists so that a future caller raising it -- three
doings before trusting a parameter, say -- changes a number rather than an
argument."""


@dataclass(frozen=True, slots=True)
class Parameter:
    """One thing a job takes as input, and what it has been given so far."""

    name: str
    """The control it was typed into: an ExtJS itemId where there is one, the
    field's own label otherwise. Named after the form rather than after the
    value, because `activityCode` says what it is and `TEST1` says what it was
    once."""

    seen: tuple[str, ...]
    """Every value observed, in the order the occurrences were seen. Two
    different values is the evidence that this varies at all."""


def _by_control(
    workflow: Workflow, gestures: Mapping[str, Gesture], intents: Mapping[str, Intent]
) -> dict[str, str]:
    """What this doing put into each control it typed into.

    Keyed by the control rather than by the step, because two doings of one job
    reach the same control at different step numbers -- the model writes the
    prose freshly each time, and a step index is its opinion. The control is
    the evidence.
    """
    found: dict[str, str] = {}
    for step in workflow.steps:
        for cited in step.cites:
            gesture = gestures.get(cited)
            if gesture is None or gesture.gesture.kind not in ("type", "select", "upload"):
                continue
            values = typed_values(gesture, intents.get(cited))
            if not values:
                # A credential, or nothing typed. typed_values refuses the
                # whole gesture when it is secret, so this is where that
                # refusal keeps a password out of a skill's parameters.
                continue
            target = gesture.gesture.target
            component = target.component if target else None
            name = (
                (component.itemId if component else None)
                or (component.fieldLabel if component else None)
                or (target.name if target else None)
                or cited
            )
            # min() rather than any(): typed_values returns a set, and a
            # parameter that changed name between runs because the set
            # iterated differently would be a phantom difference.
            found[name] = min(values)
    return found


def parameters_across(
    occurrences: Iterable[tuple[Workflow, Mapping[str, Gesture], Mapping[str, Intent]]],
) -> tuple[Parameter, ...]:
    """The controls whose value changed between doings.

    A control typed identically every time is part of the job, not an input to
    it: "click Add" is not a parameter and neither is a status every doing sets
    to the same thing. A control that changed is what the job is *about*.

    Returns nothing at all below K_MIN_OCCURRENCES, rather than returning
    everything the single doing typed. That is the whole point -- one doing
    cannot distinguish a parameter from a constant, and a list that pretends
    otherwise is worse than an empty one, because the empty one is honest.
    """
    doings = [_by_control(*occurrence) for occurrence in occurrences]
    if len(doings) < K_MIN_OCCURRENCES:
        return ()

    # Only controls every doing reached. One that appears in a single doing is
    # a difference between the recordings, not a value the job takes -- the
    # operator may simply have taken a different route that time.
    shared = set(doings[0])
    for doing in doings[1:]:
        shared &= set(doing)

    found = []
    for name in sorted(shared):
        seen = tuple(doing[name] for doing in doings)
        if len(set(seen)) > 1:
            found.append(Parameter(name=name, seen=seen))
    return tuple(found)
