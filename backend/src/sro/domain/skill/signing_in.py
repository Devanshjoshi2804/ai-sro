from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from sro.domain.observation.gesture import Gesture, Target, passed_through
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.checks import signs_in_to
from sro.domain.skill.workflow import Step, Workflow, ordered_cites


def signs_in_at(
    where: str, among: Sequence[Workflow], by_id: Mapping[str, Gesture], *, not_this: str = ""
) -> str | None:
    origin = origin_of(where)
    if not origin:
        return None
    found = [
        job.id
        for job in among
        if job.signs_in and job.id != not_this and _starts_at(job, by_id) == origin
    ]
    return found[0] if len(found) == 1 else None


def _starts_at(job: Workflow, by_id: Mapping[str, Gesture]) -> str | None:
    cited = [by_id[one] for one in ordered_cites(job) if one in by_id]
    if not cited:
        return None
    first = min(range(len(cited)), key=lambda index: (cited[index].at, index))
    return origin_of(cited[first].url or cited[first].system or "")


K_ONE_SUBMIT_S = 0.05


def sign_in_chain(job: Workflow, by_id: Mapping[str, Gesture]) -> list[Step]:
    steps = sorted(job.steps, key=lambda one: one.order)
    cited = _in_order(job, by_id)
    typed = [one.at for one in cited if _secret(one)] or [
        one.at for one in cited if one.action.kind == "type"
    ]
    landed = [
        one
        for one in cited
        if typed and one.at >= min(typed) and one.action.kind != "type" and passed_through(one)
    ]
    if not landed:
        return steps
    cut = landed[0]
    fields = [one for one in cited if one.action.kind == "type" and one.at <= cut.at]

    def refused(gesture: Gesture) -> bool:
        if gesture.at < min(typed) or passed_through(gesture):
            return False
        if origin_of(gesture.system or "") != origin_of(cut.system or ""):
            return False
        if not _submits(gesture, fields):
            return False
        if gesture.action.kind == "press" and cut.at - gesture.at <= K_ONE_SUBMIT_S:
            return True
        return any(
            before.at <= gesture.at
            and any(
                gesture.at < again.at and _same_field(before.action.target, again.action.target)
                for again in fields
            )
            for before in fields
        )

    def replayed(one: str) -> bool:
        gesture = by_id.get(one)
        if gesture is None or gesture is cut:
            return True
        return gesture.at <= cut.at and not refused(gesture)

    chain = [replace(step, cites=[one for one in step.cites if replayed(one)]) for step in steps]

    def late(step: Step) -> tuple[bool, float, int]:
        return (
            cut.id in step.cites,
            max((by_id[one].at for one in step.cites if one in by_id), default=float("-inf")),
            step.order,
        )

    holder = max((step for step in chain if cut.id in step.cites), key=lambda step: step.order)
    seen = {cut.id}
    once = []
    for step in sorted(chain, key=late):
        fresh = [one for one in step.cites if one not in seen]
        seen.update(fresh)
        if step is holder:
            fresh.append(cut.id)
        if fresh:
            once.append(replace(step, cites=fresh))
    return sorted(once, key=late)


def _submits(gesture: Gesture, typed: Sequence[Gesture]) -> bool:
    if gesture.action.kind == "press":
        return gesture.action.value in (None, "", "Enter", "NumpadEnter")
    return gesture.action.kind == "click" and not any(
        _same_field(gesture.action.target, field.action.target) for field in typed
    )


def _same_field(one: Target | None, other: Target | None) -> bool:
    if one is None or other is None:
        return False
    if one.css_path or other.css_path:
        return one.css_path == other.css_path
    return (one.tag, one.role, one.name) == (other.tag, other.role, other.name)


@dataclass(frozen=True, slots=True)
class RecordedLogin:
    job_id: str
    origin: str
    username: str | None


def recorded_login(
    where: str, among: Sequence[Workflow], by_id: Mapping[str, Gesture]
) -> RecordedLogin | None:
    system = origin_of(where)
    landing = [
        job
        for job in among
        if job.signs_in and (lands := signs_in_to(job, by_id)) is not None and lands[1] == system
    ]
    job = landing[0] if len(landing) == 1 else None
    credential = _credential(job, by_id) if job is not None else None
    if job is None or credential is None:
        return None
    origin = origin_of(credential.url or credential.system or "")
    if not origin:
        return None
    before = [
        gesture
        for gesture in _in_order(job, by_id)
        if gesture.at <= credential.at
        and gesture.action.kind == "type"
        and not _secret(gesture)
        and gesture.action.value
    ]
    return RecordedLogin(
        job_id=job.id, origin=origin, username=before[-1].action.value if before else None
    )


def _credential(job: Workflow, by_id: Mapping[str, Gesture]) -> Gesture | None:
    return next((gesture for gesture in _in_order(job, by_id) if _secret(gesture)), None)


def _in_order(job: Workflow, by_id: Mapping[str, Gesture]) -> list[Gesture]:
    cited = [by_id[one] for one in ordered_cites(job) if one in by_id]
    return sorted(cited, key=lambda gesture: gesture.at)


def _secret(gesture: Gesture) -> bool:
    target = gesture.action.target
    return bool(gesture.action.secret or (target is not None and target.secret))


__all__ = ["RecordedLogin", "recorded_login", "sign_in_chain", "signs_in_at"]
