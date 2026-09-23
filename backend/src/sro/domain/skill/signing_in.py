from __future__ import annotations

from collections.abc import Mapping, Sequence
from urllib.parse import urlsplit

from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Workflow, ordered_cites


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


__all__ = ["is_sign_in_page", "signs_in_at"]
