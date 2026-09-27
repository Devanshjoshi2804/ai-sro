from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace

from sro.domain.observation.gesture import Gesture, Intent
from sro.domain.observation.values import typed_values
from sro.domain.skill.workflow import Step, Workflow, cited_ids

K_MIN_OCCURRENCES = 2

K_PARAMETERS_RULE = 1


K_REQUIRED_MARK = "*"

TYPING = frozenset({"type", "select", "upload"})


def demanded(parameter: Mapping[str, object]) -> bool:
    said = parameter.get("required")
    if isinstance(said, bool):
        return said
    names = parameter.get("names")
    listed = names if isinstance(names, list | tuple) else ()
    return any(str(one).rstrip().endswith(K_REQUIRED_MARK) for one in listed)


def offerable(
    parameters: Sequence[Mapping[str, object]], values: Mapping[str, str]
) -> tuple[tuple[str, str], ...]:
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
    name: str

    seen: tuple[str, ...]

    key: str = ""

    in_all: bool = True

    said: bool | None = None

    @property
    def required(self) -> bool:
        if self.said is not None:
            return self.said
        return any(str(one).rstrip().endswith(K_REQUIRED_MARK) for one in self.names)

    names: tuple[str, ...] = ()


def control_names(gesture: Gesture) -> tuple[str, ...]:
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
    named = control_names(gesture)
    return named[0] if named else None


def control_key(gesture: Gesture) -> str:
    target = gesture.action.target
    component = target.component if target else None
    said = component.item_id if component else None
    return str(said).strip() if said else ""


def same_control(
    one: Iterable[str], other: Iterable[str], *, key: str = "", theirs: str = ""
) -> bool:
    if key and theirs:
        return key == theirs
    return bool({*one} & {*other})


@dataclass(frozen=True, slots=True)
class _Put:
    names: tuple[str, ...]
    key: str
    value: str
    required: bool | None = None


def _by_control(
    workflow: Workflow, gestures: Mapping[str, Gesture], intents: Mapping[str, Intent]
) -> list[_Put]:
    acted: list[tuple[str, Gesture]] = []
    for step in workflow.steps:
        for cited in step.cites:
            gesture = gestures.get(cited)
            if gesture is None or gesture.action.kind not in TYPING:
                continue
            acted.append((cited, gesture))
    acted.sort(key=lambda pair: (pair[1].at, pair[0]))

    found: list[_Put] = []
    for cited, gesture in acted:
        values = typed_values(gesture, intents.get(cited))
        if not values:
            continue
        names = control_names(gesture) or (cited,)
        key = control_key(gesture)
        typed = str(gesture.action.value).strip() if gesture.action.value else ""
        put = _Put(
            names=names,
            key=key,
            value=typed if typed in values else min(values),
            required=_page_said(gesture),
        )
        found = [
            one for one in found if not same_control(one.names, names, key=one.key, theirs=key)
        ]
        found.append(put)
    return found


def _page_said(gesture: Gesture) -> bool | None:
    target = gesture.action.target
    if target is None:
        return None
    if target.required is not None:
        return target.required
    return target.component.required if target.component is not None else None


Occurrence = tuple[Workflow, Mapping[str, Gesture], Mapping[str, Intent]]


def parameters_across(occurrences: Iterable[Occurrence]) -> tuple[LearnedParameter, ...]:
    return _told_apart([one for one, constant in _controls(occurrences) if not constant])


def constants_across(occurrences: Iterable[Occurrence]) -> tuple[LearnedParameter, ...]:
    return tuple(one for one, constant in _controls(occurrences) if constant)


def _controls(occurrences: Iterable[Occurrence]) -> list[tuple[LearnedParameter, bool]]:
    doings = [_by_control(*occurrence) for occurrence in occurrences]
    found: list[tuple[LearnedParameter, bool]] = []
    for nth, doing in enumerate(doings):
        for put in doing:
            if any(
                same_control(put.names, one.names, key=put.key, theirs=one.key) for one, _ in found
            ):
                continue
            names = list(put.names)
            key = put.key
            values = [put.value]
            said = [put.required]
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
                said.append(also.required)
            found.append(
                (
                    LearnedParameter(
                        name=names[0],
                        seen=tuple(dict.fromkeys(values)),
                        names=tuple(names),
                        key=key,
                        in_all=reached == len(doings),
                        said=next((one for one in said if one is not None), None),
                    ),
                    K_MIN_OCCURRENCES <= reached == len(doings) and len(set(values)) == 1,
                )
            )
    return found


def _told_apart(found: list[LearnedParameter]) -> tuple[LearnedParameter, ...]:
    labels = [one.name for one in found]
    return tuple(
        one
        if labels.count(one.name) == 1 or len(one.names) < 2
        else replace(one, name=one.names[1])
        for one in found
    )


def placed_doings(
    job: Workflow,
    placed: Iterable[str],
    gestures: Mapping[str, Gesture],
    intents: Mapping[str, Intent],
) -> list[Workflow]:
    own = cited_ids(job)
    typed = sorted(
        (
            gesture
            for one in placed
            if one not in own
            and (gesture := gestures.get(one)) is not None
            and gesture.action.kind in TYPING
            and typed_values(gesture, intents.get(one))
        ),
        key=lambda gesture: (gesture.stream_id, gesture.at, gesture.id),
    )
    doings: list[list[Gesture]] = []
    for gesture in typed:
        names, key = control_names(gesture) or (gesture.id,), control_key(gesture)
        if not doings or any(
            one.stream_id != gesture.stream_id
            or same_control(
                control_names(one) or (one.id,), names, key=control_key(one), theirs=key
            )
            for one in doings[-1]
        ):
            doings.append([])
        doings[-1].append(gesture)
    return [
        Workflow(
            id=job.id,
            tenant=job.tenant,
            title=job.title,
            narrative="",
            steps=[Step(order=0, says="", system=None, cites=[one.id for one in doing])],
        )
        for doing in doings
    ]
