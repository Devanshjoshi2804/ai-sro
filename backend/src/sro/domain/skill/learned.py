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

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from sro.domain.observation.gesture import Gesture, Intent
from sro.domain.observation.values import typed_values
from sro.domain.skill.workflow import Workflow

K_MIN_OCCURRENCES = 2
"""Doings needed before anything is called a parameter.

One is a recording. The name exists so that a future caller raising it -- three
doings before trusting a parameter, say -- changes a number rather than an
argument."""


K_REQUIRED_MARK = "*"
"""What a form puts on the label of a field that must be filled.

One character, and the only signal the recorder captures today: a gesture's
target carries `field_label` and no `aria-required`. Widening that is a
`make gen-recorder` change -- the recorder is generated from this side and is
never edited by hand -- and until it happens, a page that marks required
fields by colour alone tells this system nothing, which reads as optional.
"""


def demanded(parameter: Mapping[str, object]) -> bool:
    """Whether the page said this stored parameter must be filled.

    The same rule as `LearnedParameter.required`, read off a parameter as a
    job stores it. Two callers -- the runner, deciding what stops a run, and
    the question, deciding what to offer instead of demand -- and a rule kept
    in two places is a rule that drifts.

    Read off the flag where a pass has written one, and off the names
    otherwise: every parameter stored before 2026-09-22 predates the flag, and
    a migration to add it would be a migration to recompute what the names
    already carry. The flag wins where both speak, because a later pass may
    have learnt from a refusal what no label ever said.
    """
    said = parameter.get("required")
    if isinstance(said, bool):
        return said
    names = parameter.get("names")
    listed = names if isinstance(names, list | tuple) else ()
    return any(str(one).rstrip().endswith(K_REQUIRED_MARK) for one in listed)


def offerable(
    parameters: Sequence[Mapping[str, object]], values: Mapping[str, str]
) -> tuple[tuple[str, str], ...]:
    """The fields a job can fill that nobody has to, with what each was last
    time, for the ones this run has no value for.

    The last value and not every value: this is an offer somebody reads in one
    line, and "Department was IN, new, IN, OUTSIDE" is a history rather than a
    suggestion. Most recent, because `seen` is in the order the occurrences
    were seen and the newest is the likeliest to still be right.
    """
    offered: list[tuple[str, str]] = []
    for parameter in parameters:
        name = parameter.get("name")
        if not isinstance(name, str) or not name or demanded(parameter):
            continue
        if values.get(name, "").strip():
            continue
        seen = parameter.get("seen_values")
        was = [str(one) for one in seen] if isinstance(seen, list | tuple) else []
        offered.append((name, was[-1] if was else ""))
    return tuple(offered)


@dataclass(frozen=True, slots=True)
class LearnedParameter:
    """One thing a job takes as input, and what it has been given so far.

    Named for how it was found. `sro.domain.skill.parameter.Parameter` is the
    backend's own, declared on a skill; this one is the difference between two
    doings, and the two must not be mistaken for each other."""

    name: str
    """The control it was typed into, in the name a person would use: the
    field's own label where the page gives one, its ExtJS itemId otherwise.
    Named after the form rather than after the value, because `activityCode`
    says what it is and `TEST1` says what it was once."""

    seen: tuple[str, ...]
    """Every value observed, in the order the occurrences were seen. Two
    different values is the evidence that this varies at all."""

    key: str = ""
    """The page's own name for the control -- its ExtJS itemId -- where the
    recordings carried one. It is what two doings are matched on when both have
    it, because two fields can share a label and two fields cannot share an
    itemId. Empty where no recording of this control carried one."""

    in_all: bool = True
    """Whether every doing compared reached this control.

    A control two doings varied is a parameter -- that is the bar, and it does
    not change. But where a THIRD doing never reached it, the job has a route
    that does not need it, and a run taking that route must not be stopped for
    want of a value. See `_not_given`, which is where the difference is felt.
    """

    @property
    def required(self) -> bool:
        """Whether the PAGE says this field must be filled.

        Not `in_all`, which is the question this used to be answered by and is
        a different one. `in_all` says every doing compared reached the
        control, which measures what the operator happened to do -- two
        demonstrations that both filled Manufacturer made it mandatory forever,
        and a third that skipped it would flip the answer back. Requiredness
        that moves with the sample is not a fact about the warehouse.

        The marker does not move. `names` carries every name the control
        answers to, exactly as the page gave them, and a form that marks its
        mandatory fields with a star gave one of them with the star on:

            Customer Type              ["Customer Type", …, "Customer Type*"]
            Customer Type Description  ["Customer Type Description", …, "…*"]
            Department                 ["Department", "customertype-departmentNumber"]
            Manufacturer               ["Manufacturer", "customertype-manufacturerId"]

        Read off the deployment 2026-09-22. The page had been saying which two
        of the four are mandatory since the day it was demonstrated, and
        nothing read it.

        **Unknown reads as optional**, which inverts the old default, and the
        failure modes are why. A required field treated as optional reaches
        Save, the form refuses, and the screen belt says so -- one failed run,
        and the warehouse has told us something we can keep. An optional field
        treated as required cannot run at all without a value the operator may
        not have: measured 2026-09-22 at 01:24, an operator with no Manufacturer
        to give had to drop the whole job.

        A star is a convention and not a contract, which is why this is one of
        two ways to be required and not the only one. The other is a warehouse
        that refused a create for the want of a field, which is evidence
        nothing can argue with -- and which this cannot learn until it happens.
        """
        return any(str(one).rstrip().endswith(K_REQUIRED_MARK) for one in self.names)

    names: tuple[str, ...] = ()
    """Every name this one control answers to, `name` included.

    A control has as many names as the page gives it -- `Customer Type` on the
    label, `customertype-customerType` on the input -- and which of them a
    recording carries is a fact about that recording, not about the job. The
    real `Create a Customer Type` was captured both ways, so its two doings
    named the same two fields four different things and the job came to declare
    four parameters for two fields: two boxes on the offer card per value, and
    a run asked for values nobody has ever typed.

    So a parameter carries all of them, and two doings that named one control
    differently are still one control. Empty on every parameter learnt before
    this, which is why the matching that uses it still falls back to the value
    evidence."""


def control_names(gesture: Gesture) -> tuple[str, ...]:
    """Every name this control answers to, the readable one first.

    The label before the itemId, and that order is the whole of what a person
    ever sees: a parameter called `Customer Type` is one somebody can answer,
    and `customertype-customerType` is the same field wearing the name the form
    posts it under. Both are kept, because a recording carries whichever of
    them the page gave it and a later doing has to be able to find this control
    by either.
    """
    target = gesture.action.target
    component = target.component if target else None
    found = [
        (component.field_label if component else None),
        (component.item_id if component else None),
        (target.name if target else None),
    ]
    named: list[str] = []
    for one in found:
        said = str(one).strip() if one else ""
        if said and said not in named:
            named.append(said)
    return tuple(named)


def control_name(gesture: Gesture) -> str | None:
    """What one control is called, where one name is wanted. The first of
    `control_names`, which is the readable one."""
    named = control_names(gesture)
    return named[0] if named else None


def control_key(gesture: Gesture) -> str:
    """The page's own name for this control -- its ExtJS itemId -- or "".

    Kept apart from the rest of its names because it is the only one that
    answers "which control is this" rather than "what is it called". Two
    fields can share a label; two fields do not share an itemId.
    """
    target = gesture.action.target
    component = target.component if target else None
    said = component.item_id if component else None
    return str(said).strip() if said else ""


def same_control(
    one: Iterable[str], other: Iterable[str], *, key: str = "", theirs: str = ""
) -> bool:
    """Whether these name one control.

    **Where both recordings carried the page's own name, that decides.** Two
    fields on one form can share a label -- a Description in each of two
    sections -- and merging those would be one parameter where the job has two.

    **Otherwise any name in common.** A recording that carries no itemId is the
    case this exists for: `Create a Customer Type` was captured once with
    labels and once with input names, its two doings agreed on nothing, and the
    job came to declare four parameters for two fields -- four boxes on the
    offer card, two of them asking for a name nobody has ever typed.

    Deliberately not a comparison of values. `_same_control` in the mining pass
    does that, for parameters stored before any of this was recorded, and it
    merges two controls that happened to vary over one set.
    """
    if key and theirs:
        return key == theirs
    return bool({*one} & {*other})


@dataclass(frozen=True, slots=True)
class _Put:
    """One value a doing put into one control, with every name that control
    had in THAT recording."""

    names: tuple[str, ...]
    key: str
    value: str


def _by_control(
    workflow: Workflow, gestures: Mapping[str, Gesture], intents: Mapping[str, Intent]
) -> list[_Put]:
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

    found: list[_Put] = []
    for cited, gesture in acted:
        values = typed_values(gesture, intents.get(cited))
        if not values:
            # A credential, or nothing typed. typed_values refuses the whole
            # gesture when it is secret, so this is where that refusal keeps a
            # password out of a skill's parameters.
            continue
        # Every name the page gave this control, not the first one that was
        # present. Which names a recording carries varies between recordings of
        # the same form, and a control keyed on one of them is a control the
        # next doing cannot recognise.
        names = control_names(gesture) or (cited,)
        key = control_key(gesture)
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
        put = _Put(names=names, key=key, value=typed if typed in values else min(values))
        # Last wins, as it did when this was a dict: a control typed twice in
        # one doing keeps the latest value.
        found = [
            one for one in found if not same_control(one.names, names, key=one.key, theirs=key)
        ]
        found.append(put)
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

    found: list[LearnedParameter] = []
    # Every control ANY doing reached, and not only the first doing's.
    #
    # This iterated `doings[0]` -- the stored job, doing number one -- and
    # broke out the moment a later doing did not have that control. So a
    # control two LATER doings both varied was never looked at at all, and
    # because a stored job's steps never grow it could never become a
    # parameter however often it was used: an operator fills a field on
    # Tuesday and again on Wednesday, each time with a different value, and
    # the job goes on not knowing the field exists.
    #
    # The bar is unchanged. `K_MIN_OCCURRENCES` doings must have reached the
    # control and its value must have varied across them, so the reason the
    # old loop gave still holds -- one appearance is a difference between the
    # recordings rather than a value the job takes, and one value cannot be
    # told from a constant. What has gone is the accident of WHICH doing a
    # control first appeared in.
    for nth, doing in enumerate(doings):
        for put in doing:
            if any(
                same_control(put.names, one.names, key=put.key, theirs=one.key) for one in found
            ):
                continue
            names = list(put.names)
            key = put.key
            values = [put.value]
            reached = 1
            for other, elsewhere in enumerate(doings):
                if other == nth:
                    continue
                also = next(
                    (
                        one
                        for one in elsewhere
                        if same_control(one.names, names, key=one.key, theirs=key)
                    ),
                    None,
                )
                if also is None:
                    continue
                reached += 1
                names += [one for one in also.names if one not in names]
                key = key or also.key
                values.append(also.value)
            if reached >= K_MIN_OCCURRENCES and len(set(values)) > 1:
                found.append(
                    LearnedParameter(
                        # The readable name, and every name beside it. `names`
                        # is what the next doing is matched on, so a control
                        # recorded either way is recognised either way.
                        name=names[0],
                        seen=tuple(values),
                        names=tuple(names),
                        key=key,
                        in_all=reached == len(doings),
                    )
                )
    return _told_apart(found)


def _told_apart(found: list[LearnedParameter]) -> tuple[LearnedParameter, ...]:
    """Two controls that share a label are called by the names that differ.

    A form can have a Description in each of two sections. They are two
    parameters -- `same_control` kept them apart on the page's own name for
    each -- and calling both of them "Description" would put two questions
    with one wording in front of somebody, which is worse than one ugly name.
    So where a label is not unique, every control that shares it falls back to
    the name the page knows it by.
    """
    labels = [one.name for one in found]
    return tuple(
        one
        if labels.count(one.name) == 1 or len(one.names) < 2
        else LearnedParameter(name=one.names[1], seen=one.seen, names=one.names)
        for one in found
    )
