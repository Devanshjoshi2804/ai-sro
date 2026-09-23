from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from urllib.parse import urlsplit

from sro.domain.observation.gesture import Gesture, passed_through
from sro.domain.shared.hosts import origin_of
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


_SIGN_IN_PATHS = ("/oauth2/", "/protocol/openid-connect/", "/login-actions/", "/saml2/")


def is_sign_in_page(url: str | None) -> bool:
    path = urlsplit(url or "").path.lower()
    return any(marker in path + "/" for marker in _SIGN_IN_PATHS)


def _starts_at(job: Workflow, by_id: Mapping[str, Gesture]) -> str | None:
    cited = [by_id[one] for one in ordered_cites(job) if one in by_id]
    if not cited:
        return None
    first = min(range(len(cited)), key=lambda index: (cited[index].at, index))
    return origin_of(cited[first].url or cited[first].system or "")


def sign_in_chain(job: Workflow, by_id: Mapping[str, Gesture]) -> list[Step]:
    steps = sorted(job.steps, key=lambda one: one.order)
    cited = _in_order(job, by_id)
    typed = [one.at for one in cited if _secret(one)] or [
        one.at for one in cited if one.action.kind == "type"
    ]
    if not typed:
        return steps
    since = min(typed)
    for index, step in enumerate(steps):
        for one in step.cites:
            gesture = by_id.get(one)
            if (
                gesture is not None
                and gesture.at >= since
                and gesture.action.kind != "type"
                and passed_through(gesture)
            ):
                kept = [c for c in step.cites if c in by_id and by_id[c].at <= gesture.at]
                return [*steps[:index], replace(step, cites=kept)]
    return steps


@dataclass(frozen=True, slots=True)
class RecordedLogin:
    job_id: str
    origin: str
    username: str | None


def recorded_login(
    where: str, among: Sequence[Workflow], by_id: Mapping[str, Gesture]
) -> RecordedLogin | None:
    carrying = [job for job in among if job.signs_in and _credential(job, by_id) is not None]
    chosen = signs_in_at(where, carrying, by_id)
    job = next((one for one in carrying if one.id == chosen), None)
    if job is None and len(carrying) == 1:
        job = carrying[0]
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


__all__ = ["RecordedLogin", "is_sign_in_page", "recorded_login", "sign_in_chain", "signs_in_at"]
