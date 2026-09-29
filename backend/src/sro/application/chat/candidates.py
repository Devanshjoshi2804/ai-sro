from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from types import MappingProxyType

from sro.application.intent.match import words
from sro.application.skill.job_facts import JobFacts
from sro.domain.chat.asked_by import mails_behind, texts
from sro.domain.chat.request import K_CANDIDATES, Candidate
from sro.domain.execution.compose import alias_map, normal
from sro.domain.execution.evidence import writes
from sro.domain.execution.mail_job import is_mail_only, sends_mail
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.signing_in import Logins
from sro.domain.skill.workflow import Workflow, cited_ids, ordered_cites

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
        systems=frozenset(
            origin_of(facts.by_id[one].system or "")
            for one in ordered_cites(job)
            if one in facts.by_id
        )
        - {""},
    )


def _said_about(facts: JobFacts) -> frozenset[str]:
    candidate = candidate_of(facts)
    labels = [label for one in candidate.fields for label in (one.name, *one.labels)]
    return words(" ".join([candidate.title, *labels, *candidate.aliases, *candidate.asked_by]))


def _first(job: Workflow, held: Mapping[str, int]) -> tuple[int, int, str]:
    return -len(job.parameters), -held.get(job.id, 0), job.id


def _a_fragment(job: Workflow, by_id: Mapping[str, Gesture]) -> bool:
    return all(one in by_id for one in cited_ids(job)) and not any(
        writes(step, by_id) or sends_mail(step, by_id) for step in job.steps
    )


def _a_job(job: Workflow, by_id: Mapping[str, Gesture]) -> bool:
    return not job.chore and not is_mail_only(job, by_id) and not _a_fragment(job, by_id)


def real_jobs(
    jobs: Iterable[tuple[Workflow, Mapping[str, Gesture]]], *, held: Mapping[str, int] = _NONE
) -> frozenset[str]:
    copies: dict[str, list[Workflow]] = {}
    for job, by_id in jobs:
        if _a_job(job, by_id):
            copies.setdefault(normal(job.title), []).append(job)
    return frozenset(min(same, key=lambda job: _first(job, held)).id for same in copies.values())


def rank_jobs(
    said: str,
    facts: Sequence[JobFacts],
    *,
    held: Mapping[str, int] = _NONE,
    k: int = K_CANDIDATES,
) -> list[JobFacts]:
    real = real_jobs(((one.workflow, one.by_id) for one in facts), held=held)
    asked = words(said)
    ranked = sorted(
        (one for one in facts if one.workflow.id in real),
        key=lambda one: (-len(asked & _said_about(one)), *_first(one.workflow, held)),
    )
    return ranked[:k]


def chore_named(said: str, facts: Sequence[JobFacts]) -> JobFacts | None:
    asked = words(said)
    overlap = {one.workflow.id: len(asked & _said_about(one)) for one in facts}
    chores = [one for one in facts if one.workflow.chore]
    work = max((overlap[one.workflow.id] for one in facts if not one.workflow.chore), default=0)
    best = max(chores, key=lambda one: overlap[one.workflow.id], default=None)
    return best if best is not None and overlap[best.workflow.id] > work else None


__all__ = ["candidate_of", "chore_named", "rank_jobs", "real_jobs"]
