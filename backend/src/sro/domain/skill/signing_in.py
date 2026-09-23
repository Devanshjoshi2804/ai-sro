from __future__ import annotations

from collections.abc import Mapping, Sequence
from urllib.parse import urlsplit

from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Workflow


def signs_in_at(
    where: str, among: Sequence[Workflow], by_id: Mapping[str, Gesture], *, not_this: str = ""
) -> str | None:
    origin = origin_of(where)
    if not origin:
        return None
    found = [job.id for job in among if job.id != not_this and _entirely_at(job, origin, by_id)]
    return found[0] if len(found) == 1 else None


def is_a_way_in(job: Workflow, by_id: Mapping[str, Gesture]) -> bool:
    cited = [by_id[one] for step in job.steps for one in step.cites if one in by_id]
    if not cited:
        return False
    where = {origin_of(one.url or one.system or "") for one in cited}
    return len(where) == 1 and bool(next(iter(where)))


_SIGN_IN_PATHS = ("/oauth2/", "/protocol/openid-connect/", "/login-actions/", "/saml2/")


def is_sign_in_page(url: str | None) -> bool:
    path = urlsplit(url or "").path.lower()
    return any(marker in path + "/" for marker in _SIGN_IN_PATHS)


def _entirely_at(job: Workflow, origin: str, by_id: Mapping[str, Gesture]) -> bool:
    cited = [by_id[one] for step in job.steps for one in step.cites if one in by_id]
    if not cited:
        return False
    return all(origin_of(one.url or one.system or "") == origin for one in cited)


__all__ = ["is_a_way_in", "is_sign_in_page", "signs_in_at"]
