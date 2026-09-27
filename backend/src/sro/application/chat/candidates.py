from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType

from sro.application.intent.match import words
from sro.application.skill.job_facts import JobFacts
from sro.domain.chat.asked_by import mails_behind, texts
from sro.domain.chat.request import K_CANDIDATES, Candidate
from sro.domain.execution.compose import alias_map, normal
from sro.domain.skill.signing_in import Logins

_NONE: Mapping[str, int] = MappingProxyType({})


def candidate_of(facts: JobFacts, *, leave_out: str = "", logins: Logins = Logins()) -> Candidate:
    job = facts.workflow
    return Candidate(
        id=job.id,
        title=job.title,
        fields=facts.compiled.fields,
        aliases=alias_map(facts.aliases),
        seen={
            str(p["name"]): tuple(str(v) for v in p.get("seen_values", []))  # type: ignore[attr-defined]
            for p in job.parameters
            if isinstance(p.get("name"), str)
        },
        asked_by=tuple(one for one in texts(mails_behind(job, facts.by_id)) if one != leave_out),
        logins=logins,
    )


def _said_about(facts: JobFacts) -> frozenset[str]:
    candidate = candidate_of(facts)
    labels = [label for one in candidate.fields for label in (one.name, *one.labels)]
    return words(" ".join([candidate.title, *labels, *candidate.aliases, *candidate.asked_by]))


def _first(one: JobFacts, held: Mapping[str, int]) -> tuple[int, int, str]:
    job = one.workflow
    return -len(job.parameters), -held.get(job.id, 0), job.id


def rank_jobs(
    said: str,
    facts: Sequence[JobFacts],
    *,
    held: Mapping[str, int] = _NONE,
    k: int = K_CANDIDATES,
) -> list[JobFacts]:
    copies: dict[str, list[JobFacts]] = {}
    for one in facts:
        if not one.workflow.signs_in:
            copies.setdefault(normal(one.workflow.title), []).append(one)
    canonical = [min(same, key=lambda one: _first(one, held)) for same in copies.values()]
    asked = words(said)
    ranked = sorted(canonical, key=lambda one: (-len(asked & _said_about(one)), *_first(one, held)))
    return ranked[:k]


def chore_named(said: str, facts: Sequence[JobFacts]) -> JobFacts | None:
    asked = words(said)
    overlap = {one.workflow.id: len(asked & _said_about(one)) for one in facts}
    chores = [one for one in facts if one.workflow.signs_in]
    work = max((overlap[one.workflow.id] for one in facts if not one.workflow.signs_in), default=0)
    best = max(chores, key=lambda one: overlap[one.workflow.id], default=None)
    return best if best is not None and overlap[best.workflow.id] > work else None


__all__ = ["candidate_of", "chore_named", "rank_jobs"]
