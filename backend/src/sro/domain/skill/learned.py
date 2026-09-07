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

from sro.domain.observation.gesture import Gesture, Intent
from sro.domain.observation.values import typed_values
from sro.domain.skill.workflow import Workflow

K_MIN_OCCURRENCES = 2
"""Doings needed before anything is called a parameter.

One is a recording. The name exists so that a future caller raising it -- three
doings before trusting a parameter, say -- changes a number rather than an
argument."""


@dataclass(frozen=True, slots=True)
class LearnedParameter:
    """One thing a job takes as input, and what it has been given so far.

    Named for how it was found. `sro.domain.skill.parameter.Parameter` is the
    backend's own, declared on a skill; this one is the difference between two
    doings, and the two must not be mistaken for each other."""

    name: str
    """The control it was typed into: an ExtJS itemId where there is one, the
    field's own label otherwise. Named after the form rather than after the
    value, because `activityCode` says what it is and `TEST1` says what it was
    once."""

    seen: tuple[str, ...]
    """Every value observed, in the order the occurrences were seen. Two
    different values is the evidence that this varies at all."""


def control_name(gesture: Gesture) -> str | None:
    """The name a parameter takes from the control it was typed into: an
    ExtJS itemId where there is one, the field's label, else the target's
    name. One rule, used by the learning that names a parameter and by the
    shape that has to find it again."""
    target = gesture.action.target
    component = target.component if target else None
    return (
        (component.item_id if component else None)
        or (component.field_label if component else None)
        or (target.name if target else None)
    )


def _by_control(
    workflow: Workflow, gestures: Mapping[str, Gesture], intents: Mapping[str, Intent]
) -> dict[str, str]:
    """What this doing put into each control it typed into.

    Keyed by the control rather than by the step, because two doings of one job
    reach the same control at different step numbers -- the model writes the
    prose freshly each time, and a step index is its opinion. The control is
    the evidence.
    """
    # In time order, not citation order. A control typed twice in one doing --
    # `workArea` got TESTI then NEWTESTS in the real corpus -- keeps whichever
    # value is written last, and last should mean latest, not "whichever the
    # model happened to list second". Measured: 0 of 66 real steps cite out of
    # order, so this changes nothing today and stops depending on that.
    acted: list[tuple[str, Gesture]] = []
    for step in workflow.steps:
        for cited in step.cites:
            gesture = gestures.get(cited)
            if gesture is None or gesture.action.kind not in ("type", "select", "upload"):
                continue
            acted.append((cited, gesture))
    acted.sort(key=lambda pair: (pair[1].at, pair[0]))

    found: dict[str, str] = {}
    for cited, gesture in acted:
        values = typed_values(gesture, intents.get(cited))
        if not values:
            # A credential, or nothing typed. typed_values refuses the whole
            # gesture when it is secret, so this is where that refusal keeps a
            # password out of a skill's parameters.
            continue
        target = gesture.action.target
        component = target.component if target else None
        name = (
            (component.item_id if component else None)
            or (component.field_label if component else None)
            or (target.name if target else None)
            or cited
        )
        # What the OPERATOR typed, where that is known. typed_values merges the
        # operator's own value with the model's `values_seen` echo into one set
        # and provenance is gone by the time it returns -- so a doing where the
        # two disagree was being settled by string order. min() stays as the
        # fallback for a gesture with no typed value of its own (a select the
        # extension could not read, where the echo is all there is): it is
        # arbitrary, but it is arbitrary the SAME way every run, and a
        # parameter that changed value because a set iterated differently would
        # be a phantom difference. Measured: 0 of 63 real type/select/upload
        # gestures return more than one value, so nothing moves today --
        # `values_seen` is populated on 110 of 387 intents, so the mechanism is
        # armed.
        typed = str(gesture.action.value).strip() if gesture.action.value else ""
        found[name] = typed if typed in values else min(values)
    return found


def parameters_across(
    occurrences: Iterable[tuple[Workflow, Mapping[str, Gesture], Mapping[str, Intent]]],
) -> tuple[LearnedParameter, ...]:
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
            found.append(LearnedParameter(name=name, seen=seen))
    return tuple(found)
