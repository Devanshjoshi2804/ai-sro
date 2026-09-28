import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, replace
from urllib.parse import urlsplit

from sro.domain.execution.evidence import READ_METHODS, writes
from sro.domain.observation.gesture import Gesture, passed_through
from sro.domain.observation.identity import K_MIN_SHARED_STEPS, screen_of, target_identity
from sro.domain.observation.window import Window
from sro.domain.recording.background import is_background_traffic
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.learned import TYPING
from sro.domain.skill.workflow import Step, Workflow, cited_ids, ordered_cites

K_MIN_COVERAGE = 0.5
K_MAX_SKEW = 0.4

_DEFAULT_PORTS = {"http": "80", "https": "443"}


@dataclass(frozen=True, slots=True)
class Rejection:
    workflow_title: str
    reason: str
    detail: str


@dataclass(frozen=True, slots=True)
class Coverage:
    coverage: float
    skew: float
    gini: float


def validate(workflow: Workflow, evidence: dict[str, str]) -> Rejection | None:
    if not workflow.steps:
        return Rejection(workflow.title, "no steps", "a workflow of nothing")

    for step in workflow.steps:
        if not step.cites:
            return Rejection(workflow.title, "uncited step", f"step {step.order}: {step.says}")
        unknown = set(step.cites) - set(evidence)
        if unknown:
            return Rejection(workflow.title, "unknown gesture", ", ".join(sorted(unknown)))
        if not step.says.strip():
            return Rejection(workflow.title, "wordless step", f"step {step.order}")
        for used in step.uses:
            if used >= step.order:
                return Rejection(
                    workflow.title,
                    "step uses a later step",
                    f"step {step.order} uses step {used}",
                )
            if used not in {one.order for one in workflow.steps}:
                return Rejection(
                    workflow.title,
                    "step uses a step that is not there",
                    f"step {step.order} uses step {used}",
                )
        if step.system:
            touched = {evidence[cite] for cite in step.cites if evidence[cite]}
            if not touched:
                return Rejection(
                    workflow.title,
                    "unattributed evidence",
                    f"step {step.order} claims {step.system}; no cited gesture has a system",
                )
            if step.system not in touched:
                return Rejection(
                    workflow.title,
                    "step system not in evidence",
                    f"step {step.order}: {step.system}",
                )

    claimed = {s for s in workflow.systems if s}
    evidenced = {evidence[cite] for cite in cited_ids(workflow)}
    invented = claimed - evidenced
    if invented:
        return Rejection(workflow.title, "system not in evidence", ", ".join(sorted(invented)))

    if len(workflow.steps) < K_MIN_SHARED_STEPS:
        return Rejection(
            workflow.title,
            "too few steps to recognise",
            f"{len(workflow.steps)} step(s); resolve needs {K_MIN_SHARED_STEPS} to match",
        )
    return None


def _gini(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    total = sum(ordered)
    weighted = sum((index + 1) * value for index, value in enumerate(ordered))
    return (2 * weighted) / (n * total) - (n + 1) / n


def coverage(workflows: list[Workflow], window: Window) -> Coverage:
    cited: set[str] = set()
    for workflow in workflows:
        cited |= cited_ids(workflow)

    n = len(window.items)
    deciles = [0.0] * 10
    for index, item in enumerate(window.items):
        if item.gesture_id in cited:
            deciles[index * 10 // n] += 1

    total = sum(deciles)
    if total == 0:
        return Coverage(0.0, 0.0, 0.0)
    mass = [d / total for d in deciles]
    return Coverage(
        coverage=sum(1 for d in deciles if d > 0) / min(10, n),
        skew=sum(mass[:3]) - sum(mass[-3:]),
        gini=_gini(mass),
    )


_WROTE_METHODS = frozenset({"POST", "PUT", "PATCH"})


def _signed_in_here(gesture: Gesture) -> bool:
    target = gesture.action.target
    return bool(gesture.action.secret or (target is not None and target.secret))


def _did_business(gesture: Gesture) -> bool:
    here = origin_of(gesture.system or "")
    return any(
        call.status is not None
        and 200 <= call.status < 300
        and call.method.upper() in _WROTE_METHODS
        and origin_of(call.url) == here
        for call in gesture.requests
    )


def undeliverable(workflow: Workflow, gestures: dict[str, Gesture]) -> list[str]:
    can = bindable(workflow, gestures)
    return [
        str(declared["name"])
        for declared in workflow.parameters
        if declared.get("name") and str(declared["name"]) not in can
    ]


def bindable(workflow: Workflow, gestures: Mapping[str, Gesture]) -> set[str]:
    bindable: set[str] = set()
    for step in workflow.steps:
        bindable.update(step.parameters)
        for cite in step.cites:
            gesture = gestures.get(cite)
            if gesture is None or gesture.action.kind not in TYPING:
                continue
            target = gesture.action.target
            component = target.component if target else None
            for name in (
                component.item_id if component else None,
                component.field_label if component else None,
                target.name if target else None,
            ):
                if name:
                    bindable.add(name)
    return bindable


def _during(workflow: Workflow, gestures: Mapping[str, Gesture]) -> list[Gesture]:
    cited = [gestures[one] for one in ordered_cites(workflow) if one in gestures]
    if not cited:
        return []
    first, last = min(one.at for one in cited), max(one.at for one in cited)
    streams = {one.stream_id for one in cited}
    ids = {one.id for one in cited}
    systems = {origin_of(one.system or "") for one in cited}
    return [
        gesture
        for gesture in gestures.values()
        if gesture.stream_id in streams
        and first <= gesture.at <= last
        and (gesture.id in ids or origin_of(gesture.system or "") in systems)
    ]


def signs_in(workflow: Workflow, gestures: Mapping[str, Gesture]) -> bool:
    during = _during(workflow, gestures)
    own = _its_own_writes(workflow, gestures)
    return (
        any(_signed_in_here(gesture) for gesture in during)
        and not any(_did_business(gesture) and gesture.id not in own for gesture in during)
        and all(
            is_sign_in_step(workflow, step, gestures)
            for step in workflow.steps
            if writes(step, gestures)
        )
        and _only_signs_in(workflow, gestures)
    )


_SIGN_OUT = re.compile(r"(?<![a-z0-9])(?:log[\s_-]?(?:out|off)|sign[\s_-]?out)(?![a-z0-9])", re.I)
_SIGNED_OUT_PAGE = re.compile(
    r"(?<![a-z0-9])(?:(?:log(?:ged)?|sign(?:ed)?)[\s_-]?(?:in|on|out|off)"
    r"|session[\s_-]?(?:ended|expired|timeout)|auth|authorize)(?![a-z0-9])",
    re.IGNORECASE,
)


def signs_out(workflow: Workflow, gestures: Mapping[str, Gesture]) -> bool:
    cited = _in_time(workflow, gestures)
    control = next(
        (
            one
            for index, one in reversed(list(enumerate(cited)))
            if _ends_the_session(one, cited[index + 1 :])
        ),
        None,
    )
    if control is None:
        return False
    if not all(_only_reaches(one, control) for one in cited if one.at < control.at):
        return False
    if any(
        writes(replace(step, cites=[one for one in step.cites if one != control.id]), gestures)
        for step in workflow.steps
        if any(one in gestures and gestures[one].at <= control.at for one in step.cites)
    ):
        return False
    if any(_acts(one) and not _signed_out_there(one) for one in cited if one.at > control.at):
        return False
    later = min(
        (
            gesture
            for gesture in gestures.values()
            if gesture.stream_id == control.stream_id
            and gesture.tab_id == control.tab_id
            and control.at < gesture.at <= cited[-1].at + K_SITTING_GAP_S
        ),
        key=lambda gesture: (gesture.at, gesture.id),
        default=None,
    )
    return _lands_signed_out(control) or (
        later is not None and (_lands_signed_out(later) or _signed_out_there(later))
    )


def _ends_the_session(gesture: Gesture, then: list[Gesture]) -> bool:
    if gesture.action.kind not in ("click", "press"):
        return False
    target = gesture.action.target
    if target is not None and any(
        _SIGN_OUT.search(said or "") for said in (target.name, target.text)
    ):
        return True
    marks = [mark.url for mark in gesture.page_events if mark.url]
    return (
        bool(marks)
        and _lands_on_a_signed_out_page(marks[-1])
        and not _signed_out_page(gesture.page_url or gesture.url or "")
        and not any(_typed_the_credential(one) for one in then)
    )


def _only_reaches(gesture: Gesture, control: Gesture) -> bool:
    action = gesture.action
    if action.kind in ("hover", "scroll"):
        return True
    if action.kind not in ("click", "press") or action.value or _signed_in_here(gesture):
        return False
    calls = [call for call in gesture.requests if not is_background_traffic(call.url)]
    if any(call.method.upper() not in READ_METHODS for call in calls):
        return False
    if _signed_out_page(gesture.page_url or gesture.url or "") or any(
        mark.page_kind in ("navigated", "load") for mark in gesture.page_events
    ):
        return True
    return not calls and _opens(gesture, control)


def _opens(gesture: Gesture, control: Gesture) -> bool:
    target = gesture.action.target
    if target is None:
        return False
    if "aria-haspopup" in target.attributes or "aria-expanded" in target.attributes:
        return True
    opener = target.component.chain if target.component else ()
    inside = control.action.target
    within = inside.component.chain if inside is not None and inside.component else ()
    return bool(opener) and len(within) > len(opener) and within[: len(opener)] == opener


def _signed_out_page(url: str) -> bool:
    return bool(_SIGNED_OUT_PAGE.search(urlsplit(url).path))


def _lands_on_a_signed_out_page(url: str) -> bool:
    segments = [one for one in urlsplit(url).path.split("/") if one]
    return bool(segments) and bool(_SIGNED_OUT_PAGE.search(segments[-1]))


def _lands_signed_out(gesture: Gesture) -> bool:
    return any(mark.url and _signed_out_page(mark.url) for mark in gesture.page_events)


def _signed_out_there(gesture: Gesture) -> bool:
    return _signed_in_here(gesture) or _signed_out_page(gesture.page_url or gesture.url or "")


def signs_in_to(workflow: Workflow, gestures: Mapping[str, Gesture]) -> tuple[str, str] | None:
    typed = [gesture for gesture in _during(workflow, gestures) if _typed_the_credential(gesture)]
    where = {origin_of(gesture.system or "") for gesture in typed} - {""}
    if len(where) != 1:
        return None
    credential = where.pop()
    last = max(gesture.at for gesture in typed)
    ends = max(gestures[one].at for one in ordered_cites(workflow) if one in gestures)
    streams = {gesture.stream_id for gesture in typed}
    after = sorted(
        (
            gesture
            for gesture in gestures.values()
            if gesture.stream_id in streams and last <= gesture.at <= ends + K_SITTING_GAP_S
        ),
        key=lambda gesture: (gesture.at, gesture.id),
    )
    leave = next((index for index, one in enumerate(after) if _left(one, gestures)), None)
    if leave is None:
        return None
    worked = next(
        (
            origin_of(one.system or "")
            for one in after[leave + 1 :]
            if origin_of(one.system or "") not in ("", credential)
        ),
        None,
    )
    if worked is not None:
        return credential, worked
    marks = [
        origin_of(mark.url or "")
        for mark in after[leave].page_events
        if mark.url and origin_of(mark.url) not in ("", credential)
    ]
    return (credential, marks[-1]) if marks else None


def credentials_typed(workflow: Workflow, gestures: Mapping[str, Gesture]) -> Counter[str]:
    return Counter(
        field
        for step in workflow.steps
        for field in {
            f"{screen_of(gestures[one])}|{target_identity(gestures[one])}"
            for one in step.cites
            if one in gestures and _typed_the_credential(gestures[one])
        }
    )


def _in_time(workflow: Workflow, gestures: Mapping[str, Gesture]) -> list[Gesture]:
    cited = [gestures[one] for one in dict.fromkeys(ordered_cites(workflow)) if one in gestures]
    return sorted(cited, key=lambda gesture: gesture.at)


def _chain(workflow: Workflow, gestures: Mapping[str, Gesture]) -> tuple[list[Gesture], bool]:
    chain, left, _ = _split(workflow, gestures)
    return chain, left


def _split(
    workflow: Workflow, gestures: Mapping[str, Gesture]
) -> tuple[list[Gesture], bool, list[Gesture]]:
    cited = _in_time(workflow, gestures)
    first = next((index for index, one in enumerate(cited) if _signed_in_here(one)), None)
    if first is None:
        return [], False, []
    for index in range(first, len(cited)):
        if _left(cited[index], gestures):
            return cited[first : index + 1], True, cited[index + 1 :]
    return cited[first:], False, []


def _left(gesture: Gesture, gestures: Mapping[str, Gesture]) -> bool:
    if passed_through(gesture):
        return True
    here = origin_of(gesture.system or "")
    if gesture.page_events or not here:
        return False
    stream = _stream_of(gesture, gestures)
    after = next(
        (
            one
            for one in stream
            if one.id != gesture.id
            and one.tab_id == gesture.tab_id
            and gesture.at <= one.at <= gesture.at + K_SITTING_GAP_S
        ),
        None,
    )
    there = origin_of(after.system or "") if after is not None else ""
    if there in ("", here):
        return False
    _, came = _arrived(gesture, stream)
    return there in {origin_of(one.system or "") for one in came} and all(
        _identifies(one)
        for one in stream
        if origin_of(one.system or "") == here
        and one.action.kind in TYPING
        and not _signed_in_here(one)
    )


def _stream_of(gesture: Gesture, gestures: Mapping[str, Gesture]) -> list[Gesture]:
    return sorted(
        (one for one in gestures.values() if one.stream_id == gesture.stream_id),
        key=lambda one: (one.at, one.id),
    )


def _arrived(gesture: Gesture, stream: list[Gesture]) -> tuple[list[Gesture], list[Gesture]]:
    here = origin_of(gesture.system or "")
    end = next(index for index, one in enumerate(stream) if one.id == gesture.id)
    start = end
    while start > 0 and origin_of(stream[start - 1].system or "") == here:
        start -= 1
    return stream[start : end + 1], stream[:start]


_IDENTITY_TOKENS = frozenset({"username", "email"})


def _identifies(gesture: Gesture) -> bool:
    target = gesture.action.target
    if gesture.action.kind not in TYPING or target is None:
        return False
    marks = target.attributes
    tokens = set(str(marks.get("autocomplete") or "").lower().split())
    return bool(tokens & _IDENTITY_TOKENS) or str(marks.get("type") or "").lower() == "email"


def _its_own_writes(workflow: Workflow, gestures: Mapping[str, Gesture]) -> set[str]:
    chain, left = _chain(workflow, gestures)
    if not left:
        return set()
    leave = chain[-1]
    run, came = _arrived(leave, _stream_of(leave, gestures))
    starts = [one.at for one in run if _signed_in_here(one) or _identifies(one)]
    secret = [one.at for one in run if _signed_in_here(one)]
    if not came or not came[-1].system or not starts or not secret:
        return set()
    submit = min(
        (one.at for one in run if _acts(one) and one.at >= max(secret)), default=max(secret)
    )
    return {one.id for one in run if starts[0] <= one.at <= submit and _did_business(one)}


def _only_signs_in(workflow: Workflow, gestures: Mapping[str, Gesture]) -> bool:
    chain, left, after = _split(workflow, gestures)
    lands = _lands_on(workflow, gestures)
    if chain and any(
        origin_of(one.system or "") == lands
        and (_did_business(one) or one.action.kind in TYPING or bool(one.action.value))
        for one in _in_time(workflow, gestures)
        if one.at < chain[0].at
    ):
        return False
    typed_on = {origin_of(gesture.system or "") for gesture in chain if _signed_in_here(gesture)}
    if any(_acts(one) and origin_of(one.system or "") in typed_on for one in after):
        return False
    before = chain[:-1] if left else chain
    for index, gesture in enumerate(before):
        if not _acts(gesture) or (left and _on_the_credential(gesture)):
            continue
        if left and any(_typed_the_credential(later) for later in before[index + 1 :]):
            continue
        return False
    return True


def _lands_on(workflow: Workflow, gestures: Mapping[str, Gesture]) -> str | None:
    where = signs_in_to(workflow, gestures)
    return where[1] if where is not None else None


def _leaves_at(workflow: Workflow, gestures: Mapping[str, Gesture]) -> float | None:
    chain, left = _chain(workflow, gestures)
    return chain[-1].at if left else None


def _on_the_credential(gesture: Gesture) -> bool:
    target = gesture.action.target
    return gesture.action.kind != "type" and target is not None and target.secret


def _typed_the_credential(gesture: Gesture) -> bool:
    return gesture.action.kind == "type" and _signed_in_here(gesture)


def _acts(gesture: Gesture) -> bool:
    return gesture.action.kind != "type" and not (
        _on_the_credential(gesture) and gesture.action.kind == "click"
    )


def is_sign_in_step(workflow: Workflow, step: Step, gestures: Mapping[str, Gesture]) -> bool:
    own = _its_own_writes(workflow, gestures)
    cited = [gestures[one] for one in step.cites if one in gestures]
    if not cited or any(_did_business(gesture) and gesture.id not in own for gesture in cited):
        return False
    mine = replace(step, cites=[one for one in step.cites if one not in own])
    typed = [one.at for one in _in_time(workflow, gestures) if _typed_the_credential(one)]
    lands = _lands_on(workflow, gestures)
    if (
        typed
        and lands is not None
        and not writes(mine, gestures)
        and all(one.at < min(typed) and origin_of(one.system or "") != lands for one in cited)
    ):
        return True
    leaves = _leaves_at(workflow, gestures)
    if leaves is not None and any(gesture.at > leaves for gesture in cited):
        return False
    left = any(_left(gesture, gestures) for gesture in cited)
    acts = [
        gesture
        for gesture in cited
        if _acts(gesture) and not (left and _on_the_credential(gesture))
    ]
    if not all(_left(gesture, gestures) for gesture in acts):
        return False
    carries = _carries_the_credential(step, gestures)
    if carries and not writes(mine, gestures):
        return True
    return (carries or _after_the_credential(workflow, step, gestures)) and left


def _carries_the_credential(step: Step, gestures: Mapping[str, Gesture]) -> bool:
    return any(_signed_in_here(gestures[one]) for one in step.cites if one in gestures)


def _after_the_credential(workflow: Workflow, step: Step, gestures: Mapping[str, Gesture]) -> bool:
    before = [one for one in workflow.steps if one.order < step.order]
    if not before:
        return False
    previous = max(before, key=lambda one: one.order)
    here = {origin_of(gestures[one].system or "") for one in step.cites if one in gestures}
    return any(
        _signed_in_here(gestures[one]) and origin_of(gestures[one].system or "") in here
        for one in previous.cites
        if one in gestures
    )


def work_only(
    workflow: Workflow, gestures: dict[str, Gesture], *, ours: frozenset[str]
) -> Rejection | None:
    cited = [gestures[one] for one in ordered_cites(workflow) if one in gestures]
    order = [gesture.system or "" for gesture in cited]
    last = {system: index for index, system in enumerate(order)}
    bounced = {gesture.system or "" for gesture in cited if passed_through(gesture)}
    transit = {
        system
        for system, index in last.items()
        if system and index < len(order) - 1 and system in bounced
    }

    during = _during(workflow, gestures)
    if (
        any(_signed_in_here(gesture) for gesture in during)
        and any(passed_through(gesture) for gesture in during)
        and not any(_did_business(gesture) for gesture in during)
    ):
        return Rejection(
            workflow.title,
            "not a job",
            "a credential was typed, the browser moved on, and nothing was written",
        )

    kept = [
        system
        for system in workflow.systems
        if origin_of(system) not in ours and system not in transit
    ]
    if workflow.systems and not kept:
        return Rejection(
            workflow.title,
            "not a job",
            "every system it names is this deployment or a hop through one",
        )
    workflow.systems = kept
    return None


K_SITTING_GAP_S = 600.0


def _sittings(times: list[float]) -> list[tuple[float, float]]:
    spans: list[tuple[float, float]] = []
    for at in sorted(times):
        if spans and at - spans[-1][1] <= K_SITTING_GAP_S:
            spans[-1] = (spans[-1][0], at)
        else:
            spans.append((at, at))
    return spans


def one_occurrence(workflow: Workflow, gestures: dict[str, Gesture]) -> None:
    times = [gestures[cited].at for cited in cited_ids(workflow) if cited in gestures]
    if not times:
        return
    spans = _sittings(times)
    if len(spans) < 2:
        return

    def reach(span: tuple[float, float]) -> tuple[int, float]:
        lo, hi = span
        steps = sum(
            1
            for step in workflow.steps
            if any(cited in gestures and lo <= gestures[cited].at <= hi for cited in step.cites)
        )
        return steps, hi

    lo, hi = max(spans, key=reach)
    for step in workflow.steps:
        step.cites = [
            cited for cited in step.cites if cited in gestures and lo <= gestures[cited].at <= hi
        ]
