"""Reading a loop off two demonstrations that did the same block a different
number of times.

"Adjust every short-shipped line on this order" is one task, and two honest
demonstrations of it disagree about how many steps it has. Induction refused
that pair outright -- *the runs are not two runs of one task* -- which was the
one thing it could say that was certainly wrong.

The shape recognised here is narrow, and every part of it is checked against
both runs:

- the block repeats **whole**, the same block in both runs, a different number
  of times;
- an **earlier step's response** carried a list whose length is exactly that
  number, in each run, at the same pointer;
- every value the block sends that changes from one iteration to the next is a
  field of the element being acted on, at the **same place in the element**,
  in every iteration of both runs.

The last rule is what makes this evidence. WebRobot (PLDI 2022, and
docs/16-what-others-have-solved.md) calls the equivalent test speculate and
validate: a guessed loop must predict actions it was not built from, or it is
memorisation with a data structure around it.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.induction import jsonutil
from sro.application.induction.diff import (
    Difference,
    Substitution,
    _diff_action,
    _diff_request,
    _mutations,
    url_shape,
)
from sro.application.induction.errors import InductionFailed
from sro.application.induction.naming import deduplicate, singular, suggest_name
from sro.application.induction.sites import parse_json
from sro.domain.recording.events import ActionFrame
from sro.domain.skill.loop import Binding, Loop
from sro.domain.skill.parameter import Parameter, ParameterKind


@dataclass(frozen=True, slots=True)
class LoopFound:
    loop: Loop
    parameters: tuple[Parameter, ...]
    substitutions: dict[int, tuple[Substitution, ...]]
    keep: int
    """How many frames of each run survive: the prefix and one iteration. The
    rest are the same block again and have nothing left to prove."""


def detect(
    frames_a: tuple[ActionFrame, ...],
    frames_b: tuple[ActionFrame, ...],
    *,
    taken: set[str] | None = None,
) -> LoopFound | None:
    """The loop these two runs are two lengths of, if they are.

    None for everything else, which is nearly everything: a pair that is not a
    loop must reach the ordinary refusals unchanged, and a wrong loop is a
    warehouse doing something once per row of a list nobody meant.
    """
    shapes_a = [_shape(frame) for frame in frames_a]
    shapes_b = [_shape(frame) for frame in frames_b]
    if len(frames_a) == len(frames_b):
        # Two runs that did the same number of things prove nothing about
        # looping. They are a task that does three similar things, and the
        # ordinary diff has always read that correctly.
        return None
    if any(len(_mutations(frame)) > 1 for frame in (*frames_a, *frames_b)):
        # One gesture that made two calls is split into two steps later, which
        # renumbers everything a loop names. Refused rather than guessed at.
        return None

    # Where the block starts is not a guess: the prefix is only right if an
    # earlier response holds a list as long as the number of iterations that
    # prefix implies -- in *each* run. Tried shortest first, so the loop starts
    # as early as the evidence allows.
    for prefix in range(1, min(len(shapes_a), len(shapes_b))):
        if shapes_a[:prefix] != shapes_b[:prefix]:
            break
        found = _try(frames_a, frames_b, shapes_a, shapes_b, prefix, set(taken or ()))
        if found is not None:
            return found
    return None


def _try(
    frames_a: tuple[ActionFrame, ...],
    frames_b: tuple[ActionFrame, ...],
    shapes_a: list[str],
    shapes_b: list[str],
    prefix: int,
    taken: set[str],
) -> LoopFound | None:
    block = _block_length(shapes_a[prefix:], shapes_b[prefix:])
    if block is None:
        return None

    times_a = (len(frames_a) - prefix) // block
    times_b = (len(frames_b) - prefix) // block
    source = _source_of(frames_a, frames_b, prefix, times_a, times_b)
    if source is None:
        return None
    source_index, pointer = source

    binds, substitutions, parameters = _bindings(
        frames_a,
        frames_b,
        prefix=prefix,
        block=block,
        source=source_index,
        pointer=pointer,
        times=(times_a, times_b),
        taken=taken,
    )
    if not binds:
        return None

    return LoopFound(
        loop=Loop(
            over_step_index=source_index,
            over_pointer=pointer,
            first_step=prefix,
            last_step=prefix + block - 1,
            binds=binds,
        ),
        parameters=parameters,
        substitutions=substitutions,
        keep=prefix + block,
    )


def _shape(frame: ActionFrame) -> str:
    """What makes two frames the same step of one task, for this purpose: the
    control, and the call it made with its identifiers taken out."""
    target = frame.action.target
    named = (target.accessible_name or target.text or target.css_path or "") if target else ""
    request = frame.primary_request
    call = f"{request.method.upper()} {url_shape(request.url)}" if request else ""
    return f"{frame.action.kind}|{named}|{call}"


def _block_length(tail_a: list[str], tail_b: list[str]) -> int | None:
    """The shortest block both tails are whole repetitions of.

    Shortest because it claims the least: a body of one step repeated four times
    is a stronger reading of the same evidence than a body of two repeated
    twice, and it is the one that keeps working when the third demonstration has
    five.
    """
    if not tail_a or not tail_b:
        return None
    for block in range(1, min(len(tail_a), len(tail_b)) + 1):
        unit = tail_a[:block]
        if unit != tail_b[:block]:
            continue
        if len(tail_a) % block or len(tail_b) % block:
            continue
        if _repeats(tail_a, unit) and _repeats(tail_b, unit):
            # The counts differ by construction: `detect` refuses two runs of
            # equal length, and both tails start at the same prefix.
            return block
    return None


def _repeats(tail: list[str], unit: list[str]) -> bool:
    return all(tail[at : at + len(unit)] == unit for at in range(0, len(tail), len(unit)))


def _source_of(
    frames_a: tuple[ActionFrame, ...],
    frames_b: tuple[ActionFrame, ...],
    prefix: int,
    times_a: int,
    times_b: int,
) -> tuple[int, str] | None:
    """The earlier response that said how many there would be.

    The same pointer of the same step in both runs, holding a list as long as
    that run's own number of iterations. Anything less is a coincidence: a page
    of results happens to have three rows in the run that did three things.
    """
    for index in range(prefix):
        for pointer, listed in _arrays(frames_a[index]):
            if len(listed) != times_a:
                continue
            other = dict(_arrays(frames_b[index])).get(pointer)
            if other is not None and len(other) == times_b:
                return index, pointer
    return None


def _arrays(frame: ActionFrame) -> list[tuple[str, list[jsonutil.JsonValue]]]:
    found: list[tuple[str, list[jsonutil.JsonValue]]] = []
    for request in frame.requests:
        document = parse_json(request.response_text)
        if document is None:
            continue
        found.extend(_arrays_in(document))
    return found


def _arrays_in(
    value: jsonutil.JsonValue, prefix: str = ""
) -> list[tuple[str, list[jsonutil.JsonValue]]]:
    found: list[tuple[str, list[jsonutil.JsonValue]]] = []
    if isinstance(value, list):
        found.append((prefix or "/", list(value)))
    elif isinstance(value, dict):
        for key, child in value.items():
            found.extend(_arrays_in(child, f"{prefix}/{jsonutil.escape(str(key))}"))
    return found


def _bindings(
    frames_a: tuple[ActionFrame, ...],
    frames_b: tuple[ActionFrame, ...],
    *,
    prefix: int,
    block: int,
    source: int,
    pointer: str,
    times: tuple[int, int],
    taken: set[str],
) -> tuple[tuple[Binding, ...], dict[int, tuple[Substitution, ...]], tuple[Parameter, ...]]:
    """Which values the block sends are fields of the thing it is acting on.

    Read off what changes from one iteration to the next, and then required to
    hold for *every* iteration of *both* runs -- including the first, which is
    the one the skill keeps. A rule that explains the iterations it was read
    from and not the others is the memorisation this is arranged against.
    """
    elements_a = _elements(frames_a[source], pointer)
    elements_b = _elements(frames_b[source], pointer)
    if len(elements_a) != times[0] or len(elements_b) != times[1]:
        return (), {}, ()

    # Grouped by where in the element the value comes from, not by where it is
    # sent: Blue Yonder's adjust puts the line id in the path and in the body,
    # and two parameters that always hold the same value is how a reviewer ends
    # up reading a plan that looks like a mis-binding.
    places: dict[str, list[tuple[int, Difference]]] = {}
    for offset in range(block):
        for difference in _varies(frames_a, prefix, block, offset, times[0]):
            place = _place_in_element(
                difference, frames_a, frames_b, prefix, block, offset, elements_a, elements_b, times
            )
            if place is not None:
                places.setdefault(place, []).append((prefix + offset, difference))

    binds: list[Binding] = []
    substitutions: dict[int, list[Substitution]] = {}
    parameters: list[Parameter] = []
    named: set[str] = set(taken)

    for place, sites in places.items():
        _, first = sites[0]
        name = deduplicate(singular(suggest_name(first.site, url=first.url)), named)
        named.add(name)
        binds.append(Binding(parameter=name, pointer=place))
        for step, difference in sites:
            substitutions.setdefault(step, []).append(
                Substitution(site=difference.site, parameter=name)
            )
        parameters.append(
            Parameter(
                name=name,
                kind=ParameterKind.ITERATED,
                description=f"{place.lstrip('/')} of each thing at {pointer}",
                observed_values=tuple(
                    _text(jsonutil.get(element, place)) for element in elements_a[:2]
                ),
                source_step_index=source,
                source_pointer=place,
            )
        )

    return tuple(binds), {k: tuple(v) for k, v in substitutions.items()}, tuple(parameters)


def _varies(
    frames: tuple[ActionFrame, ...], prefix: int, block: int, offset: int, times: int
) -> list[Difference]:
    """Sites where this position of the block sent something different the
    second time round."""
    first = frames[prefix + offset]
    if times < 2:
        return []
    second = frames[prefix + block + offset]
    try:
        return [
            *_diff_action(prefix + offset, first, second),
            *_diff_request(prefix + offset, first, second),
        ]
    except InductionFailed:
        return []


def _place_in_element(
    difference: Difference,
    frames_a: tuple[ActionFrame, ...],
    frames_b: tuple[ActionFrame, ...],
    prefix: int,
    block: int,
    offset: int,
    elements_a: list[jsonutil.JsonValue],
    elements_b: list[jsonutil.JsonValue],
    times: tuple[int, int],
) -> str | None:
    """Where inside one element this value lives -- if the same place explains
    every iteration of both runs.

    Read off the first run's first two iterations, then required to hold for all
    of them and for the other run's as well. A place that explains only what it
    was read from explains nothing.
    """
    sent_a = _per_iteration(
        frames_a, prefix, block, offset, times[0], difference, difference.value_a
    )
    first_b = _at_site(
        frames_a[prefix + offset], frames_b[prefix + offset], prefix + offset, difference
    )
    sent_b = _per_iteration(
        frames_b, prefix, block, offset, times[1], difference, first_b or difference.value_a
    )

    for place, leaf in jsonutil.leaves(elements_a[0]):
        if _text(leaf) != difference.value_a:
            continue
        if all(
            _text(jsonutil.get(elements[index], place)) == value
            for elements, values in ((elements_a, sent_a), (elements_b, sent_b))
            for index, value in enumerate(values)
        ):
            return place
    return None


def _per_iteration(
    frames: tuple[ActionFrame, ...],
    prefix: int,
    block: int,
    offset: int,
    times: int,
    difference: Difference,
    first: str,
) -> list[str]:
    """What this run sent at this site, iteration by iteration.

    Read by diffing each iteration against the first: a site that does not
    appear in that diff sent the same thing the first one did.
    """
    values = [first]
    at = frames[prefix + offset]
    for iteration in range(1, times):
        later = frames[prefix + iteration * block + offset]
        values.append(_at_site(at, later, prefix + offset, difference) or first)
    return values


def _at_site(
    one: ActionFrame, other: ActionFrame, index: int, difference: Difference
) -> str | None:
    try:
        found = [*_diff_action(index, one, other), *_diff_request(index, one, other)]
    except InductionFailed:
        return None
    return next((d.value_b for d in found if d.site == difference.site), None)


def _elements(frame: ActionFrame, pointer: str) -> list[jsonutil.JsonValue]:
    for found, listed in _arrays(frame):
        if found == pointer:
            return listed
    return []


def _text(value: jsonutil.JsonValue) -> str:
    return jsonutil.as_text(value)
